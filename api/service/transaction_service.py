from typing import List, Optional
from discord.ext import commands
from database import get_connection
from ..models.transaction import TransactionResponse, TransactionCreate
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TransactionService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def get_recent_transactions(self, limit: int = 10) -> List[TransactionResponse]:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, growid, type, details, old_balance, new_balance, created_at
                FROM transactions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            transactions = []
            
            for row in results:
                transactions.append(TransactionResponse(
                    id=row['id'],
                    growid=row['growid'],
                    type=row['type'],
                    details=row['details'],
                    old_balance=row['old_balance'],
                    new_balance=row['new_balance'],
                    created_at=datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
                ))
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def get_user_transactions(self, growid: str) -> List[TransactionResponse]:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, growid, type, details, old_balance, new_balance, created_at
                FROM transactions
                WHERE growid = ? COLLATE binary
                ORDER BY created_at DESC
                LIMIT 50
            """, (growid,))
            
            results = cursor.fetchall()
            transactions = []
            
            for row in results:
                transactions.append(TransactionResponse(
                    id=row['id'],
                    growid=row['growid'],
                    type=row['type'],
                    details=row['details'],
                    old_balance=row['old_balance'],
                    new_balance=row['new_balance'],
                    created_at=datetime.strptime(row['created_at'], '%Y-%m-%d %H:%M:%S')
                ))
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions for {growid}: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def create_transaction(self, transaction: TransactionCreate) -> TransactionResponse:
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
            """, (transaction.growid,))
            
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"GrowID {transaction.growid} not found")
            
            old_balance = f"{result['balance_wl']}|{result['balance_dl']}|{result['balance_bgl']}"
            
            # Insert transaction
            cursor.execute("""
                INSERT INTO transactions (
                    growid, type, details, old_balance, new_balance, items_count
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transaction.growid,
                transaction.type,
                transaction.details,
                old_balance,
                old_balance,  # New balance will be updated by other services
                1
            ))
            
            transaction_id = cursor.lastrowid
            
            conn.commit()
            logger.info(f"Created transaction for {transaction.growid}: {transaction.type}")
            
            # Return created transaction
            return TransactionResponse(
                id=transaction_id,
                growid=transaction.growid,
                type=transaction.type,
                details=transaction.details,
                old_balance=old_balance,
                new_balance=old_balance,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error creating transaction for {transaction.growid}: {e}")
            raise
        finally:
            if conn:
                conn.close()