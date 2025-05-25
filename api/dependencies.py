from fastapi import Depends, HTTPException
from discord.ext import commands

class BotInstance:
    _instance = None
    
    def set_bot(self, bot: commands.Bot):
        self._instance = bot
    
    def get_bot(self) -> commands.Bot:
        if not self._instance:
            raise HTTPException(status_code=503, detail="Bot instance not available")
        return self._instance

get_bot_instance = BotInstance()

async def get_bot():
    return get_bot_instance.get_bot()