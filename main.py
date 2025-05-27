import discord
from discord.ext import commands
import os
import json
import logging
import asyncio
import aiohttp
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, UTC
from threading import Thread
import traceback

# Import local modules
from api.server import create_api_server
from database import setup_database, get_connection
from utils.command_handler import AdvancedCommandHandler
from utils.button_handler import ButtonHandler
from api.config import config, API_VERSION

# Setup logging directory
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)

# Create formatter with current user
current_user = "fdygg"  # Current user's login
formatter = logging.Formatter(
    '%(asctime)s UTC - %(name)s - %(levelname)s - [User: ' + current_user + ']\n'
    'Message: %(message)s\n'
    'Path: %(pathname)s\n'
    'Function: %(funcName)s\n'
    'Line: %(lineno)d\n'
    'Details: %(exc_info)s\n'
)

# Setup file handler
file_handler = logging.FileHandler(log_dir / f'bot_{datetime.now().strftime("%Y%m%d")}.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Setup console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Setup root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Setup specific loggers
loggers = ['uvicorn', 'fastapi', 'api', 'database', 'discord', 'admin']
for logger_name in loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True

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
            logger.debug("Loading configuration file...")
            with open('config.json', 'r') as f:
                config = json.load(f)

            # Validate and convert types
            for key, expected_type in required_keys.items():
                if key not in config:
                    logger.error(f"Missing required config key: {key}")
                    raise KeyError(f"Missing required key: {key}")
                
                if isinstance(expected_type, tuple):
                    if not isinstance(config[key], expected_type):
                        config[key] = expected_type[0](config[key])
                else:
                    if not isinstance(config[key], expected_type):
                        config[key] = expected_type(config[key])

            logger.info("Configuration loaded successfully")
            return config

        except Exception as e:
            logger.error(f"""
            Configuration error:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)
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

        logger.debug(f"""
        Bot initialized with:
        Admin ID: {self.admin_id}
        Guild ID: {self.guild_id}
        Live Stock Channel: {self.live_stock_channel_id}
        Purchase Log Channel: {self.log_purchase_channel_id}
        Donation Log Channel: {self.donation_log_channel_id}
        History Buy Channel: {self.history_buy_channel_id}
        Startup Time: {self.startup_time}
        """)

    async def setup_hook(self):
        """Initialize bot components"""
        try:
            logger.debug("Setting up bot components...")
            
            # Initialize command handler
            if not self._command_handler_ready:
                self.command_handler = AdvancedCommandHandler(self)
                self._command_handler_ready = True
                logger.debug("Command handler initialized")
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            logger.debug("aiohttp session created")
            
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
                    logger.error(f"""
                    Failed to load extension:
                    Extension: {ext}
                    Error: {str(e)}
                    Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                    Stack Trace:
                    {traceback.format_exc()}
                    """)
                    
        except Exception as e:
            logger.error(f"""
            Setup error:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)

    async def close(self):
        """Cleanup on shutdown"""
        logger.debug("Performing cleanup...")
        if self.session:
            await self.session.close()
            logger.debug("aiohttp session closed")
        await super().close()
        logger.info("Bot shutdown complete")

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
            logger.debug("Bot status updated")
            
        except Exception as e:
            logger.error(f"""
            Ready event error:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)

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
                logger.info(f"""
                Channel Message:
                Channel: {message.channel.name}
                Author: {message.author}
                Content: {message.content}
                Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                """)

            # Process commands
            if message.content.startswith(self.command_prefix):
                await self.process_commands(message)
                
        except Exception as e:
            logger.error(f"""
            Message handling error:
            Error: {str(e)}
            Channel: {message.channel.name}
            Author: {message.author}
            Content: {message.content}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)

    async def on_interaction(self, interaction: discord.Interaction):
        """Interaction event handler"""
        try:
            if interaction.type == discord.InteractionType.component:
                logger.debug(f"""
                Button interaction:
                User: {interaction.user}
                Custom ID: {interaction.data.get('custom_id')}
                Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                """)
                await self.button_handler.handle_button(interaction)
        except Exception as e:
            logger.error(f"""
            Interaction error:
            Error: {str(e)}
            User: {interaction.user}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)

    async def on_command_error(self, ctx, error):
        """Command error handler"""
        try:
            if isinstance(error, commands.CommandNotFound):
                return

            command_name = ctx.command.name if ctx.command else ctx.invoked_with
            
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("❌ You don't have permission!", delete_after=5)
                logger.warning(f"""
                Missing permissions:
                User: {ctx.author}
                Command: {command_name}
                Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                """)
            elif isinstance(error, commands.CommandOnCooldown):
                await ctx.send(
                    f"⏰ Wait {error.retry_after:.1f}s!",
                    delete_after=5
                )
                logger.debug(f"""
                Command on cooldown:
                User: {ctx.author}
                Command: {command_name}
                Retry After: {error.retry_after:.1f}s
                Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                """)
            else:
                logger.error(f"""
                Command error:
                Command: {command_name}
                Error: {str(error)}
                User: {ctx.author}
                Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
                Stack Trace:
                {traceback.format_exc()}
                """)
                await ctx.send("❌ Command error!", delete_after=5)
                
        except Exception as e:
            logger.error(f"""
            Error handler error:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)

def main():
    """Main entry point"""
    try:
        logger.info(f"""
        Starting application:
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        User: {current_user}
        Python Version: {sys.version}
        """)
        
        # Load config
        bot_config = Config.load()
        
        # Setup database
        logger.debug("Setting up database...")
        setup_database()
        
        # Create bot instance
        logger.debug("Creating bot instance...")
        bot = MyBot(bot_config)
        
        # Setup API server
        logger.debug("Setting up API server...")
        api = create_api_server(bot)
        
        # Run bot
        logger.info("Starting bot...")
        bot.run(bot_config['token'], reconnect=True)
        
    except Exception as e:
        logger.critical(f"""
        Fatal error:
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        
    finally:
        # Cleanup
        try:
            logger.debug("Performing cleanup...")
            conn = get_connection()
            if conn:
                conn.close()
                logger.debug("Database connection closed")
        except Exception as e:
            logger.error(f"""
            Database cleanup error:
            Error: {str(e)}
            Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)

if __name__ == '__main__':
    main()