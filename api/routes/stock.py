from fastapi import APIRouter, Depends
from typing import List
from ..models.stock import StockResponse, StockItem
from ..service.stock_service import StockService
from ..dependencies import get_bot

router = APIRouter()

@router.get("/", response_model=List[StockResponse])
async def get_all_stock(bot=Depends(get_bot)):
    service = StockService(bot)
    return await service.get_all_stock()

@router.get("/{product_code}", response_model=StockResponse)
async def get_stock(product_code: str, bot=Depends(get_bot)):
    service = StockService(bot)
    stock = await service.get_stock(product_code)
    if not stock:
        raise HTTPException(status_code=404, detail="Product not found")
    return stock