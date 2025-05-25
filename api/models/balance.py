from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BalanceResponse(BaseModel):
    growid: str
    balance_wl: int
    balance_dl: int
    balance_bgl: int
    updated_at: Optional[datetime] = None

class BalanceUpdateRequest(BaseModel):
    amount: int