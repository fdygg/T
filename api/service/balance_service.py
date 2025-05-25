from typing import Optional, Dict
from discord.ext import commands
from database import get_connection
from ..models.balance import BalanceResponse, BalanceUpdateRequest
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BalanceService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    async def get_balance(self, growid: str) -> Optional[BalanceResponse]:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT balance_wl, balance_dl, balance_bgl, updated_at
                FROM users
                WHERE growid = ? COLLATE binary
            """, (growid,))
            result = cursor.fetchone()
            
            if result:
                return BalanceResponse(
                    growid=growid,
                    balance_wl=result['balance_wl'],
                    balance_dl=result['balance_dl'],
                    balance_bgl=result['balance_bgl'],
                    updated_at=datetime.strptime(result['updated_at'], '%Y-%m-%d %H:%M:%S')
                )
            return None
            
        except Exception as e:
            logger.error(f"Error getting balance for {growid}: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def add_balance(self, growid: str, amount: int) -> BalanceResponse:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Get current balance
            cursor.execute("""
                SELECT balance_wl, balance_dl, balance_bgl
                FROM users
                WHERE growid = ? COLLATE binary
                FOR UPDATE
            """, (growid,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f"GrowID {growid} not found")
            
            # Calculate new balance
            new_wl = result['balance_wl'] + amount
            
            # Convert WL to DL and BGL if needed
            new_dl = result['balance_dl']
            new_bgl = result['balance_bgl']
            
            if new_wl >= 100:
                dl_to_add = new_wl // 100
                new_wl = new_wl % 100
                new_dl += dl_to_add
                
                if new_dl >= 100:
                    bgl_to_add = new_dl // 100
                    new_dl = new_dl % 100
                    new_bgl += bgl_to_add
            
            # Update balance
            cursor.execute("""
                UPDATE users
                SET balance_wl = ?,
                    balance_dl = ?,
                    balance_bgl = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE growid = ? COLLATE binary
            """, (new_wl, new_dl, new_bgl, growid))
            
            # Log transaction
            cursor.execute("""
                INSERT INTO transactions (
                    growid, type, details, old_balance, new_balance, items_count
                ) VALUES (?, 'ADD', ?, ?, ?, ?)
            """, (
                growid,
                f"Added {amount} WL via API",
                f"{result['balance_wl']}|{result['balance_dl']}|{result['balance_bgl']}",
                f"{new_wl}|{new_dl}|{new_bgl}",
                1
            ))
            
            conn.commit()
            logger.info(f"Added {amount} WL to {growid}")
            
            # Return updated balance
            return await self.get_balance(growid)
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error adding balance for {growid}: {e}")
            raise
        finally:
            if conn:
                conn.close()