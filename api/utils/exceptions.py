class ProductManagerError(Exception):
    """Base exception for product manager errors"""
    pass

class TransactionError(Exception):
    """Exception for transaction-related errors"""
    pass
class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class NotFoundError(APIError):
    """Error for resource not found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)

class ValidationError(APIError):
    """Error for validation failures"""
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=400)

class UnauthorizedError(APIError):
    """Error for unauthorized access"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)