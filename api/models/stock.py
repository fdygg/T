from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class StockStatus(str, Enum):
    AVAILABLE = "available"
    SOLD = "sold"
    RESERVED = "reserved"
    EXPIRED = "expired"
    INVALID = "invalid"

class StockItem(BaseModel):
    id: Optional[int] = None
    product_code: str = Field(..., description="Product code this stock belongs to")
    content: str = Field(..., min_length=1, description="Stock content (world name, account details, etc)")
    status: StockStatus = Field(default=StockStatus.AVAILABLE)
    added_by: str = Field(default="fdygg")
    added_at: datetime = Field(
        default_factory=lambda: datetime.strptime("2025-05-28 14:57:46", "%Y-%m-%d %H:%M:%S")
    )
    updated_at: Optional[datetime] = None
    buyer_id: Optional[str] = None
    seller_id: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "product_code": "FARM_WORLD",
                "content": "FARMWORLD1",
                "status": "available",
                "added_by": "fdygg",
                "added_at": "2025-05-28 14:57:46",
                "metadata": {
                    "world_type": "farm",
                    "has_magplant": True
                }
            }
        }

class StockAddRequest(BaseModel):
    product_code: str = Field(..., description="Product code to add stock to")
    items: List[str] = Field(..., min_items=1, description="List of stock contents to add")
    metadata: Optional[Dict] = Field(default_factory=dict)
    
    @validator('items')
    def validate_items(cls, v):
        if not all(item.strip() for item in v):
            raise ValueError("Stock items cannot be empty")
        return [item.strip() for item in v]

    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "FARM_WORLD",
                "items": ["FARMWORLD1", "FARMWORLD2"],
                "metadata": {
                    "world_type": "farm",
                    "has_magplant": True
                }
            }
        }

class StockReduceRequest(BaseModel):
    product_code: str = Field(..., description="Product code to reduce stock from")
    quantity: int = Field(..., gt=0, description="Quantity to reduce")
    reason: Optional[str] = Field(None, max_length=200)
    operation_by: str = Field(default="fdygg")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_code": "FARM_WORLD",
                "quantity": 1,
                "reason": "Manual adjustment",
                "operation_by": "fdygg"
            }
        }

class StockFilter(BaseModel):
    product_code: Optional[str] = None
    status: Optional[StockStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    added_by: Optional[str] = None
    buyer_id: Optional[str] = None
    seller_id: Optional[str] = None
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError("End date must be after start date")
        return v

class StockHistoryResponse(BaseModel):
    items: List[StockItem]
    total: int
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    filters: Optional[StockFilter] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "product_code": "FARM_WORLD",
                        "content": "FARMWORLD1",
                        "status": "available",
                        "added_by": "fdygg",
                        "added_at": "2025-05-28 14:57:46",
                        "metadata": {
                            "world_type": "farm",
                            "has_magplant": True
                        }
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
                "filters": {
                    "product_code": "FARM_WORLD",
                    "status": "available"
                }
            }
        }