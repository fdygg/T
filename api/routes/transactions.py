from fastapi import APIRouter, Depends
from typing import List
from ..models.transaction import TransactionResponse, TransactionCreate
from ..service.transaction_service import TransactionService
from ..dependencies import get_bot

router = APIRouter()

@router.get("/", response_model=List[TransactionResponse])
async def get_transactions(limit: int = 10, bot=Depends(get_bot)):
    service = TransactionService(bot)
    return await service.get_recent_transactions(limit)

@router.get("/{growid}", response_model=List[TransactionResponse])
async def get_user_transactions(growid: str, bot=Depends(get_bot)):
    service = TransactionService(bot)
    return await service.get_user_transactions(growid)