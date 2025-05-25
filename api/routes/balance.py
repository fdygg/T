from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models.balance import BalanceResponse, BalanceUpdateRequest
from ..service.balance_service import BalanceService
from ..dependencies import get_bot

router = APIRouter()

@router.get("/{growid}", response_model=BalanceResponse)
async def get_balance(growid: str, bot=Depends(get_bot)):
    service = BalanceService(bot)
    balance = await service.get_balance(growid)
    if not balance:
        raise HTTPException(status_code=404, detail="GrowID not found")
    return balance

@router.post("/{growid}/add", response_model=BalanceResponse)
async def add_balance(growid: str, request: BalanceUpdateRequest, bot=Depends(get_bot)):
    service = BalanceService(bot)
    try:
        balance = await service.add_balance(growid, request.amount)
        return balance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))