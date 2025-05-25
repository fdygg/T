import discord
from discord.ext import commands
from .balance_manager import BalanceManagerService
from database import get_connection
import logging
from datetime import datetime

class Donate(commands.Cog):
    """
    Cog untuk menangani sistem donasi otomatis
    Menerima webhook dengan format:
    GrowID: nama_grow_id
    Deposit: jumlah (WL/DL/BGL)
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.balance_service = BalanceManagerService(bot)
        self.logger = logging.getLogger('donate')

    @commands.Cog.listener()
    async def on_message(self, message):
        # Hanya proses pesan dari webhook yang mengandung format yang benar
        if not (message.webhook_id and "GrowID:" in message.content and "Deposit:" in message.content):
            return

        try:
            # Parse informasi dari pesan
            growid, deposit = self._parse_message(message.content)
            if not (growid and deposit):
                self.logger.warning(f"Invalid donation format received: {message.content}")
                return

            # Hitung total WL dari deposit
            wl, dl, bgl = self._parse_currency_amount(deposit)
            total_wl = wl + (dl * 100) + (bgl * 10000)  # Konversi ke WL

            # Dapatkan Discord ID dari GrowID
            discord_id = await self._get_discord_id(growid)
            if not discord_id:
                self.logger.warning(f"GrowID tidak terdaftar: {growid}")
                if hasattr(self.bot, 'donation_log_channel_id'):
                    log_channel = self.bot.get_channel(self.bot.donation_log_channel_id)
                    if log_channel:
                        await log_channel.send(f"⚠️ [DONASI GAGAL] GrowID '{growid}' tidak terdaftar dalam database.")
                return

            # Proses penambahan balance
            await self.balance_service.add_balance(discord_id, total_wl)

            # Kirim log donasi
            await self._send_donation_log(growid, total_wl, deposit)
            
        except Exception as e:
            self.logger.error(f"Error processing donation: {str(e)}", exc_info=True)
            if hasattr(self.bot, 'donation_log_channel_id'):
                log_channel = self.bot.get_channel(self.bot.donation_log_channel_id)
                if log_channel:
                    await log_channel.send(f"❌ [ERROR] Gagal memproses donasi: {str(e)}")

    def _parse_message(self, content: str) -> tuple[str, str]:
        """Parse pesan webhook untuk mendapatkan GrowID dan deposit"""
        growid = None
        deposit = None
        
        for line in content.splitlines():
            if "GrowID:" in line:
                growid = line.split("GrowID:")[-1].strip()
            elif "Deposit:" in line:
                deposit = line.split("Deposit:")[-1].strip()
                
        return growid, deposit

    def _parse_currency_amount(self, text: str) -> tuple[int, int, int]:
        """Parse jumlah currency dari text deposit"""
        wl = dl = bgl = 0
        text = text.lower()
        parts = [p.strip() for p in text.split(",")]
        
        for part in parts:
            amount = int("".join(filter(str.isdigit, part)) or 0)
            if "world lock" in part or "wl" in part:
                wl += amount
            elif "diamond lock" in part or "dl" in part:
                dl += amount
            elif "blue gem lock" in part or "bgl" in part:
                bgl += amount
                
        return wl, dl, bgl

    async def _get_discord_id(self, growid: str) -> int:
        """Dapatkan Discord ID dari GrowID"""
        conn = None
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM users WHERE growid = ?", (growid,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            if conn:
                conn.close()

    async def _send_donation_log(self, growid: str, total_wl: int, deposit_text: str):
        """Kirim log donasi ke channel yang ditentukan"""
        if not hasattr(self.bot, 'donation_log_channel_id'):
            return
            
        log_channel = self.bot.get_channel(self.bot.donation_log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="🎉 Donasi Diterima!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="GrowID", value=growid, inline=True)
            embed.add_field(name="Total", value=f"{total_wl:,} WL", inline=True)
            embed.add_field(name="Deposit", value=deposit_text, inline=False)
            
            await log_channel.send(embed=embed)

async def setup(bot):  # Diubah menjadi async setup untuk kompatibilitas
    await bot.add_cog(Donate(bot))