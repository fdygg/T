# main.py
import discord
from discord.ext import commands
import os
import json
import logging
import asyncio
import aiohttp
import sqlite3
from pathlib import Path
from datetime import datetime, UTC
from threading import Thread

# Import local modules
from database import setup_database, get_connection
from utils.command_handler import AdvancedCommandHandler
from utils.button_handler import ButtonHandler
from fastapi import FastAPI
import uvicorn
from api.routes import router as api_router
from api.middleware import setup_middleware
from api.dependencies import get_bot_instance

# Setup logging
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / 'bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class Config:
    @staticmethod
    def load():
        """Load and validate config"""
        required_keys = {
            'token': str,
            'guild_id': (int, str),
            'admin_id': (int, str),
            'id_live_stock': (int, str),
            'id_log_purch': (int, str),
            'id_donation_log': (int, str),
            'id_history_buy': (int, str),
            'channels': dict,
            'roles': dict,
            'cooldowns': dict,
            'permissions': dict,
            'rate_limits': dict
        }
        
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)

            # Validate and convert types
            for key, expected_type in required_keys.items():
                if key not in config:
                    raise KeyError(f"Missing required key: {key}")
                
                if isinstance(expected_type, tuple):
                    if not isinstance(config[key], expected_type):
                        config[key] = expected_type[0](config[key])
                else:
                    if not isinstance(config[key], expected_type):
                        config[key] = expected_type(config[key])

            return config

        except Exception as e:
            logger.error(f"Config error: {e}")
            raise

class MyBot(commands.Bot):
    def __init__(self, config):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=commands.DefaultHelpCommand(
                no_category='Commands',
                sort_commands=True,
                dm_help=False,
                show_hidden=False,
                verify_checks=True
            )
        )
        
        # Initialize bot attributes
        self.config = config
        self.session = None
        self.startup_time = datetime.now(UTC)
        self._command_handler_ready = False
        self.button_handler = ButtonHandler(self)
        
        # Set IDs from config
        self.admin_id = int(config['admin_id'])
        self.guild_id = int(config['guild_id'])
        self.live_stock_channel_id = int(config['id_live_stock'])
        self.log_purchase_channel_id = int(config['id_log_purch'])
        self.donation_log_channel_id = int(config['id_donation_log'])
        self.history_buy_channel_id = int(config['id_history_buy'])

    async def setup_hook(self):
        """Initialize bot components"""
        try:
            # Initialize command handler
            if not self._command_handler_ready:
                self.command_handler = AdvancedCommandHandler(self)
                self._command_handler_ready = True
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            # Load extensions
            extensions = [
                'cogs.admin',
                'ext.live_stock',
                'ext.trx',
                'ext.donate',
                'ext.balance_manager',
                'ext.product_manager'
            ]
            
            for ext in extensions:
                try:
                    await self.load_extension(ext)
                    logger.info(f'✅ Loaded extension: {ext}')
                except Exception as e:
                    logger.error(f'❌ Failed to load {ext}: {e}')
                    logger.exception(f"Detailed error loading {ext}:")
                    
        except Exception as e:
            logger.error(f"Setup error: {e}")
            logger.exception("Detailed setup error:")

    async def close(self):
        """Cleanup on shutdown"""
        if self.session:
            await self.session.close()
        await super().close()

    async def on_ready(self):
        """Bot ready event handler"""
        try:
            logger.info(f'Bot {self.user.name} is ready!')
            logger.info(f'Bot ID: {self.user.id}')
            logger.info(f'Guild ID: {self.guild_id}')
            logger.info(f'Admin ID: {self.admin_id}')
            
            # Verify channels
            guild = self.get_guild(self.guild_id)
            if not guild:
                logger.error(f"Guild not found: {self.guild_id}")
                return

            channels = {
                'Live Stock': self.live_stock_channel_id,
                'Purchase Log': self.log_purchase_channel_id,
                'Donation Log': self.donation_log_channel_id,
                'History Buy': self.history_buy_channel_id,
                'Music': int(self.config['channels']['music']),
                'Logs': int(self.config['channels']['logs'])
            }

            for name, channel_id in channels.items():
                channel = guild.get_channel(channel_id)
                if channel:
                    logger.info(f"✅ Found {name} channel: {channel.name}")
                else:
                    logger.error(f"❌ Channel not found: {name} ({channel_id})")

            # Set status
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="Growtopia Shop | !help"
                ),
                status=discord.Status.online
            )
            
        except Exception as e:
            logger.error(f"Ready event error: {e}")
            logger.exception("Detailed ready error:")

    async def on_message(self, message):
        """Message event handler"""
        if message.author.bot:
            return

        try:
            # Log important channel messages
            if message.channel.id in [
                self.live_stock_channel_id,
                self.log_purchase_channel_id,
                self.donation_log_channel_id,
                self.history_buy_channel_id
            ]:
                logger.info(
                    f'Channel {message.channel.name}: '
                    f'{message.author}: {message.content}'
                )

            # Process commands
            if message.content.startswith(self.command_prefix):
                await self.process_commands(message)
                
        except Exception as e:
            logger.error(f"Message handling error: {e}")

    async def on_interaction(self, interaction: discord.Interaction):
        """Interaction event handler"""
        if interaction.type == discord.InteractionType.component:
            await self.button_handler.handle_button(interaction)

    async def on_command_error(self, ctx, error):
        """Command error handler"""
        try:
            if isinstance(error, commands.CommandNotFound):
                return

            command_name = ctx.command.name if ctx.command else ctx.invoked_with
            
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ You don't have permission!", delete_after=5)
            elif isinstance(error, commands.CommandOnCooldown):
                await ctx.send(
                    f"⏰ Wait {error.retry_after:.1f}s!",
                    delete_after=5
                )
            else:
                logger.error(f"Command error in {command_name}: {error}")
                logger.exception("Detailed command error:")
                await ctx.send("❌ Command error!", delete_after=5)
                
        except Exception as e:
            logger.error(f"Error handler error: {e}")

class APIServer:
    def __init__(self, bot):
        self.app = FastAPI(
            title="Discord Bot API",
            description="Backend API for Growtopia Shop Bot",
            version="1.0.0"
        )
        self.bot = bot
        self.setup_api()

    def setup_api(self):
        """Setup API routes and middleware"""
        get_bot_instance.set_bot(self.bot)
        self.app.include_router(api_router, prefix="/api/v1")
        setup_middleware(self.app)

    def run(self):
        """Run API server"""
        uvicorn.run(self.app, host="0.0.0.0", port=8080)

def main():
    """Main entry point"""
    try:
        # Load config
        config = Config.load()
        
        # Setup database
        setup_database()
        
        # Create bot instance
        bot = MyBot(config)
        
        # Setup API server
        api = APIServer(bot)
        api_thread = Thread(target=api.run, daemon=True)
        api_thread.start()
        
        # Run bot
        bot.run(config['token'], reconnect=True)
        
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.exception("Detailed fatal error:")
        
    finally:
        # Cleanup
        try:
            conn = get_connection()
            if conn:
                conn.close()
        except Exception as e:
            logger.error(f"Database cleanup error: {e}")

if __name__ == '__main__':
    main()