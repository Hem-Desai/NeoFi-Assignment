from fastapi import status


class AppException(Exception):
    """base exception class for application exceptions"""
    
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        self.detail = detail
        self.status_code = status_code


class AuthenticationError(AppException):
    """exception raised for authentication errors"""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(AppException):
    """exception raised for authorization errors"""
    
    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(detail, status_code=status.HTTP_403_FORBIDDEN)


class ResourceNotFoundError(AppException):
    """exception raised when a resource is not found"""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class ConflictError(AppException):
    """exception raised for conflicts (e.g., overlapping events)"""
    
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(detail, status_code=status.HTTP_409_CONFLICT)


class ValidationError(AppException):
    """exception raised for validation errors"""
    
    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
