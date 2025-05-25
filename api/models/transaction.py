from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionCreate(BaseModel):
    growid: str
    type: str
    amount: int
    details: str

class TransactionResponse(BaseModel):
    id: int
    growid: str
    type: str
    details: str
    old_balance: str
    new_balance: str
    created_at: datetime