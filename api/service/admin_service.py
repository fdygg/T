from typing import Dict, List
from discord.ext import commands
from database import get_connection
from datetime import datetime, timedelta
import bcrypt
import logging

logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def verify_admin(self, username: str, password: str) -> bool:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get admin credentials
            cursor.execute("""
                SELECT password_hash
                FROM admins
                WHERE username = ? AND is_active = 1
            """, (username,))
            
            result = cursor.fetchone()
            if not result:
                return False
                
            # Verify password
            return bcrypt.checkpw(
                password.encode('utf-8'),
                result['password_hash']
            )
            
        except Exception as e:
            logger.error(f"Error verifying admin: {e}")
            return False
        finally:
            if conn:
                conn.close()

    async def get_dashboard_stats(self) -> Dict:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get total users
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total_users = cursor.fetchone()['count']
            
            # Get total stock
            cursor.execute("SELECT COUNT(*) as count FROM stock WHERE status = 'available'")
            total_stock = cursor.fetchone()['count']
            
            # Get today's sales
            today = datetime.utcnow().date()
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE DATE(created_at) = ?
                AND type = 'PURCHASE'
            """, (today.isoformat(),))
            today_sales = cursor.fetchone()['count']
            
            # Get total revenue
            cursor.execute("""
                SELECT SUM(total_price) as total
                FROM transactions
                WHERE type = 'PURCHASE'
            """)
            total_revenue = cursor.fetchone()['total'] or 0
            
            # Get recent transactions
            cursor.execute("""
                SELECT *
                FROM transactions
                ORDER BY created_at DESC
                LIMIT 5
            """)
            recent_transactions = cursor.fetchall()
            
            # Get chart data (last 7 days)
            labels = []
            data = []
            for i in range(6, -1, -1):
                date = (today - timedelta(days=i))
                labels.append(date.strftime("%Y-%m-%d"))
                
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM transactions
                    WHERE DATE(created_at) = ?
                    AND type = 'PURCHASE'
                """, (date.isoformat(),))
                count = cursor.fetchone()['count']
                data.append(count)
            
            return {
                "total_users": total_users,
                "total_stock": total_stock,
                "today_sales": today_sales,
                "total_revenue": total_revenue,
                "recent_transactions": recent_transactions,
                "chart_labels": labels,
                "chart_data": data
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            raise
        finally:
            if conn:
                conn.close()