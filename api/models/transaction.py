from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict
from enum import Enum
from decimal import Decimal

class TransactionType(str, Enum):
    PURCHASE = "purchase"
    REFUND = "refund"
    RESTOCK = "restock"
    VOID = "void"
    ADJUSTMENT = "adjustment"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    VOIDED = "voided"
    REFUNDED = "refunded"

class TransactionCreate(BaseModel):
    growid: str = Field(..., min_length=3, description="Buyer's Growtopia ID")
    type: TransactionType = Field(..., description="Type of transaction")
    amount: int = Field(..., gt=0, description="Transaction amount in World Locks")
    details: str = Field(..., min_length=3, description="Transaction details")
    items: Optional[list[int]] = Field(None, description="List of stock item IDs")
    metadata: Optional[Dict] = Field(default_factory=dict)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "growid": "PLAYER123",
                "type": "purchase",
                "amount": 100,
                "details": "Purchase of 1x Farm World",
                "items": [1],
                "metadata": {
                    "world_name": "FARMWORLD1",
                    "purchase_method": "manual"
                }
            }
        }

class TransactionResponse(BaseModel):
    id: int = Field(..., description="Transaction ID")
    growid: str = Field(..., description="Buyer's Growtopia ID")
    type: TransactionType
    details: str
    amount: int = Field(..., description="Transaction amount")
    old_balance: int = Field(..., description="Balance before transaction")
    new_balance: int = Field(..., description="Balance after transaction")
    status: TransactionStatus = Field(default=TransactionStatus.COMPLETED)
    items: Optional[list[Dict]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 12345,
                "growid": "PLAYER123",
                "type": "purchase",
                "details": "Purchase of 1x Farm World",
                "amount": 100,
                "old_balance": 1000,
                "new_balance": 900,
                "status": "completed",
                "items": [
                    {
                        "id": 1,
                        "content": "FARMWORLD1",
                        "type": "world"
                    }
                ],
                "created_at": "2025-05-28T14:43:41",
                "updated_at": None,
                "metadata": {
                    "world_name": "FARMWORLD1",
                    "purchase_method": "manual"
                }
            }
        }

class TransactionFilter(BaseModel):
    growid: Optional[str] = None
    type: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    min_amount: Optional[int] = Field(None, ge=0)
    max_amount: Optional[int] = Field(None, ge=0)
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError("End date must be after start date")
        return v
    
    @validator('max_amount')
    def validate_amounts(cls, v, values):
        if v and 'min_amount' in values and values['min_amount']:
            if v < values['min_amount']:
                raise ValueError("Max amount must be greater than min amount")
        return v