from typing import List, Optional, Dict
from discord.ext import commands
from database import get_connection
from ..models.stock import StockResponse, StockItem
import logging

logger = logging.getLogger(__name__)

class StockService:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def get_all_stock(self) -> List[StockResponse]:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get all products with their stock count
            cursor.execute("""
                SELECT 
                    p.code,
                    p.name,
                    p.price,
                    COUNT(CASE WHEN s.status = 'available' THEN 1 END) as available,
                    GROUP_CONCAT(
                        CASE WHEN s.status = 'available' 
                        THEN json_object('id', s.id, 'content', s.content, 'status', s.status)
                        END
                    ) as items
                FROM products p
                LEFT JOIN stock s ON p.code = s.product_code
                GROUP BY p.code, p.name, p.price
                ORDER BY p.code
            """)
            
            results = cursor.fetchall()
            stock_list = []
            
            for row in results:
                items = []
                if row['items']:
                    items_data = row['items'].split(',')
                    for item_data in items_data:
                        if item_data:
                            item_dict = eval(item_data)  # Convert string to dict
                            items.append(StockItem(**item_dict))
                
                stock_list.append(StockResponse(
                    code=row['code'],
                    name=row['name'],
                    price=row['price'],
                    available=row['available'],
                    items=items
                ))
            
            return stock_list
            
        except Exception as e:
            logger.error(f"Error getting all stock: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def get_stock(self, product_code: str) -> Optional[StockResponse]:
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Get product details and available stock
            cursor.execute("""
                SELECT 
                    p.code,
                    p.name,
                    p.price,
                    COUNT(CASE WHEN s.status = 'available' THEN 1 END) as available,
                    GROUP_CONCAT(
                        CASE WHEN s.status = 'available' 
                        THEN json_object('id', s.id, 'content', s.content, 'status', s.status)
                        END
                    ) as items
                FROM products p
                LEFT JOIN stock s ON p.code = s.product_code
                WHERE p.code = ?
                GROUP BY p.code, p.name, p.price
            """, (product_code,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            items = []
            if row['items']:
                items_data = row['items'].split(',')
                for item_data in items_data:
                    if item_data:
                        item_dict = eval(item_data)  # Convert string to dict
                        items.append(StockItem(**item_dict))
            
            return StockResponse(
                code=row['code'],
                name=row['name'],
                price=row['price'],
                available=row['available'],
                items=items
            )
            
        except Exception as e:
            logger.error(f"Error getting stock for {product_code}: {e}")
            raise
        finally:
            if conn:
                conn.close()