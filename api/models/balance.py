from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BalanceResponse(BaseModel):
    growid: str
    balance: int
    donation_total: Optional[int] = 0
    purchase_total: Optional[int] = 0
    last_updated: Optional[datetime] = None
    status: str = "success"
    
    class Config:
        json_schema_extra = {
            "example": {
                "growid": "PLAYER123",
                "balance": 1000000,
                "donation_total": 2000000,
                "purchase_total": 1000000,
                "last_updated": "2025-05-26T06:17:09",
                "status": "success"
            }
        }

class BalanceUpdateRequest(BaseModel):
    amount: int
    transaction_type: str  # "add" or "subtract"
    reason: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1000000,
                "transaction_type": "add",
                "reason": "Donation"
            }
        }

class BalanceHistoryResponse(BaseModel):
    growid: str
    transactions: list[dict]
    total_records: int
    status: str = "success"

    class Config:
        json_schema_extra = {
            "example": {
                "growid": "PLAYER123",
                "transactions": [
                    {
                        "type": "donation",
                        "amount": 1000000,
                        "timestamp": "2025-05-26T06:17:09",
                        "description": "Diamond Lock donation"
                    }
                ],
                "total_records": 1,
                "status": "success"
            }
        }