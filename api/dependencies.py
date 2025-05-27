import logging
from datetime import datetime
import traceback
from functools import lru_cache
from typing import Optional
from discord.ext import commands

logger = logging.getLogger(__name__)

class BotInstanceManager:
    def __init__(self):
        self._bot: Optional[commands.Bot] = None
        logger.debug("BotInstanceManager initialized")

    def set_bot(self, bot: commands.Bot):
        """Set the bot instance"""
        try:
            logger.debug(f"""
            Setting bot instance:
            Bot: {bot.__class__.__name__}
            Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """)
            self._bot = bot
        except Exception as e:
            logger.error(f"""
            Error setting bot instance:
            Error: {str(e)}
            Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)
            raise

    def get_bot(self) -> commands.Bot:
        """Get the bot instance"""
        if not self._bot:
            logger.error("Bot instance not set")
            raise RuntimeError("Bot instance not initialized")
        return self._bot

    async def get_bot_async(self) -> commands.Bot:
        """Get the bot instance asynchronously"""
        try:
            return self.get_bot()
        except Exception as e:
            logger.error(f"""
            Error getting bot instance:
            Error: {str(e)}
            Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            Stack Trace:
            {traceback.format_exc()}
            """)
            raise

_bot_manager = BotInstanceManager()

# Export these functions for use in other modules
def set_bot(bot: commands.Bot):
    """Set the bot instance"""
    _bot_manager.set_bot(bot)

def get_bot() -> commands.Bot:
    """Get the bot instance synchronously"""
    return _bot_manager.get_bot()

@lru_cache()
async def get_bot_async() -> commands.Bot:
    """Get the bot instance asynchronously"""
    return await _bot_manager.get_bot_async()

# For backwards compatibility
get_bot_instance = _bot_manager