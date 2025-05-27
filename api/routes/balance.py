from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime, UTC, timedelta
import logging
import traceback
from ..dependencies import get_bot
from ..models.balance import (
    BalanceResponse,
    BalanceUpdateRequest,
    BalanceHistoryResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

def create_cached_response(data: dict, cache_time: int = 60):
    """Create response with cache headers"""
    headers = {
        "Cache-Control": f"public, max-age={cache_time}",
        "Expires": (datetime.now(UTC) + timedelta(seconds=cache_time)).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        ),
    }
    return JSONResponse(content=data, headers=headers)

@router.get("/{growid}", response_model=BalanceResponse)
async def get_balance(growid: str):
    """Get balance for a GrowID"""
    try:
        logger.debug(f"""
        Get balance request:
        GrowID: {growid}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        
        bot = get_bot()
        balance_manager = bot.get_cog("BalanceManagerCog")
        
        if not balance_manager:
            logger.error("BalanceManagerCog not found")
            raise HTTPException(
                status_code=500,
                detail="Balance manager not available"
            )
            
        balance = await balance_manager.get_balance(growid)
        donation_total = await balance_manager.get_donation_total(growid)
        purchase_total = await balance_manager.get_purchase_total(growid)
        
        response = BalanceResponse(
            growid=growid,
            balance=balance,
            donation_total=donation_total,
            purchase_total=purchase_total,
            last_updated=datetime.now(UTC),
            status="success"
        )
        
        logger.debug(f"Balance response: {response.dict()}")
        return create_cached_response(response.dict(), cache_time=30)
        
    except Exception as e:
        logger.error(f"""
        Error getting balance:
        GrowID: {growid}
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.post("/{growid}/update", response_model=BalanceResponse)
async def update_balance(
    growid: str,
    request: BalanceUpdateRequest
):
    """Update balance for a GrowID"""
    try:
        logger.debug(f"""
        Update balance request:
        GrowID: {growid}
        Amount: {request.amount}
        Type: {request.transaction_type}
        Reason: {request.reason}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        
        bot = get_bot()
        balance_manager = bot.get_cog("BalanceManagerCog")
        
        if not balance_manager:
            logger.error("BalanceManagerCog not found")
            raise HTTPException(
                status_code=500,
                detail="Balance manager not available"
            )
            
        if request.transaction_type == "add":
            await balance_manager.add_balance(growid, request.amount, request.reason)
        elif request.transaction_type == "subtract":
            await balance_manager.subtract_balance(growid, request.amount, request.reason)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid transaction type. Must be 'add' or 'subtract'"
            )
            
        # Get updated balance
        balance = await balance_manager.get_balance(growid)
        donation_total = await balance_manager.get_donation_total(growid)
        purchase_total = await balance_manager.get_purchase_total(growid)
        
        response = BalanceResponse(
            growid=growid,
            balance=balance,
            donation_total=donation_total,
            purchase_total=purchase_total,
            last_updated=datetime.now(UTC),
            status="success"
        )
        
        logger.debug(f"Balance updated successfully: {response.dict()}")
        return response
        
    except Exception as e:
        logger.error(f"""
        Error updating balance:
        GrowID: {growid}
        Request: {request.dict()}
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/{growid}/history", response_model=BalanceHistoryResponse)
async def get_balance_history(
    growid: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get balance history for a GrowID"""
    try:
        logger.debug(f"""
        Get balance history request:
        GrowID: {growid}
        Limit: {limit}
        Offset: {offset}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        """)
        
        bot = get_bot()
        balance_manager = bot.get_cog("BalanceManagerCog")
        
        if not balance_manager:
            logger.error("BalanceManagerCog not found")
            raise HTTPException(
                status_code=500,
                detail="Balance manager not available"
            )
            
        transactions = await balance_manager.get_transaction_history(
            growid,
            limit=limit,
            offset=offset
        )
        
        total_records = await balance_manager.get_transaction_count(growid)
        
        response = BalanceHistoryResponse(
            growid=growid,
            transactions=transactions,
            total_records=total_records,
            status="success"
        )
        
        logger.debug(f"History response: {response.dict()}")
        return create_cached_response(response.dict(), cache_time=60)
        
    except Exception as e:
        logger.error(f"""
        Error getting balance history:
        GrowID: {growid}
        Error: {str(e)}
        Time: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC
        Stack Trace:
        {traceback.format_exc()}
        """)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# Add documentation route
@router.get("/docs/balance")
async def balance_docs():
    """Get API documentation for balance endpoints"""
    return {
        "endpoints": {
            "GET /{growid}": {
                "description": "Get balance for a GrowID",
                "parameters": {
                    "growid": "string"
                },
                "cache": "30 seconds"
            },
            "POST /{growid}/update": {
                "description": "Update balance for a GrowID",
                "parameters": {
                    "growid": "string",
                    "amount": "integer",
                    "transaction_type": "'add' or 'subtract'",
                    "reason": "string"
                }
            },
            "GET /{growid}/history": {
                "description": "Get transaction history for a GrowID",
                "parameters": {
                    "growid": "string",
                    "limit": "integer (1-100), default: 10",
                    "offset": "integer >= 0, default: 0"
                },
                "cache": "60 seconds"
            }
        },
        "models": {
            "BalanceResponse": {
                "growid": "string",
                "balance": "integer",
                "donation_total": "integer",
                "purchase_total": "integer",
                "last_updated": "datetime",
                "status": "string"
            }
        }
    }