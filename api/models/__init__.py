from datetime import datetime, UTC

from .balance import (
    BalanceResponse,
    BalanceUpdateRequest,
    BalanceHistoryResponse
)

from .transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionType,
    TransactionStatus,
    TransactionFilter
)

from .product import (
    ProductType,
    ProductStatus,
    ProductBase,
    ProductCreate,
    ProductUpdate,
    ProductResponse
)

from .stock import (
    StockStatus,
    StockItem,
    StockAddRequest,
    StockReduceRequest,
    StockFilter,
    StockHistoryResponse
)

from .auth import (
    Token,
    TokenData,
    LoginRequest,
    LoginResponse
)

__all__ = [
    # Balance models
    'BalanceResponse',
    'BalanceUpdateRequest',
    'BalanceHistoryResponse',
    
    # Transaction models
    'TransactionCreate',
    'TransactionResponse',
    'TransactionType',
    'TransactionStatus',
    'TransactionFilter',
    
    # Product models
    'ProductType',
    'ProductStatus',
    'ProductBase',
    'ProductCreate',
    'ProductUpdate',
    'ProductResponse',
    
    # Stock models
    'StockStatus',
    'StockItem',
    'StockAddRequest',
    'StockReduceRequest',
    'StockFilter',
    'StockHistoryResponse',
    
    # Auth models
    'Token',
    'TokenData',
    'LoginRequest',
    'LoginResponse'
]

def get_current_time() -> str:
    """Get current time in UTC YYYY-MM-DD HH:MM:SS format"""
    return datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')