from fastapi import APIRouter

router = APIRouter()

from .routes.routes_balance import router as balance_router      
from .routes.routes_stock import router as stock_router 
from .routes.routes_transactions import router as transactions_router

router.include_router(balance_router, prefix="/balance", tags=["Balance"])
router.include_router(stock_router, prefix="/stock", tags=["Stock"])
router.include_router(transactions_router, prefix="/transactions", tags=["Transactions"])

@router.get("/health")
async def health_check():
    return {"status": "ok"}