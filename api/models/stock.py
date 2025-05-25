from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class StockItem(BaseModel):
    id: int
    content: str
    status: str

class StockResponse(BaseModel):
    code: str
    name: str
    price: int
    available: int
    items: list[StockItem]