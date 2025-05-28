from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal
from datetime import datetime
from decimal import Decimal
from enum import Enum

class TransactionType(str, Enum):
    ADD = "add"
    SUBTRACT = "subtract"
    DONATION = "donation"
    PURCHASE = "purchase"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REVERSED = "reversed"
    CANCELLED = "cancelled"

class BalanceResponse(BaseModel):
    growid: str = Field(..., description="The Growtopia ID of the user")
    balance: int = Field(..., ge=0, description="Current balance in World Locks")
    donation_total: Optional[int] = Field(0, ge=0, description="Total donations received")
    purchase_total: Optional[int] = Field(0, ge=0, description="Total purchases made")
    last_updated: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Last balance update timestamp"
    )
    status: str = Field("success", description="Response status")
    
    @validator('balance', 'donation_total', 'purchase_total')
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v
    
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
    amount: int = Field(..., gt=0, description="Amount to add or subtract")
    transaction_type: TransactionType = Field(
        ..., 
        description="Type of transaction"
    )
    reason: Optional[str] = Field(
        None,
        min_length=3,
        max_length=200,
        description="Reason for the transaction"
    )
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1000000,
                "transaction_type": "add",
                "reason": "Diamond Lock donation"
            }
        }

class Transaction(BaseModel):
    id: str = Field(..., description="Unique transaction ID")
    type: TransactionType
    amount: int = Field(..., gt=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    description: Optional[str] = None
    status: TransactionStatus = Field(default=TransactionStatus.SUCCESS)
    metadata: Optional[dict] = Field(default_factory=dict)

class BalanceHistoryResponse(BaseModel):
    growid: str = Field(..., description="The Growtopia ID of the user")
    transactions: List[Transaction] = Field(
        default_factory=list,
        description="List of transactions"
    )
    total_records: int = Field(..., ge=0, description="Total number of records")
    status: str = Field("success", description="Response status")
    page: Optional[int] = Field(1, ge=1, description="Current page number")
    page_size: Optional[int] = Field(10, ge=1, le=100, description="Records per page")
    
    class Config:
        json_schema_extra = {
            "example": {
                "growid": "PLAYER123",
                "transactions": [
                    {
                        "id": "txn_123456",
                        "type": "donation",
                        "amount": 1000000,
                        "timestamp": "2025-05-26T06:17:09",
                        "description": "Diamond Lock donation",
                        "status": "success",
                        "metadata": {
                            "donor_name": "DONOR123",
                            "donation_type": "diamond_lock"
                        }
                    }
                ],
                "total_records": 1,
                "status": "success",
                "page": 1,
                "page_size": 10
            }
        }