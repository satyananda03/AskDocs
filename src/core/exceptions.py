class AppException(Exception):
    """Base exception for application"""
    pass

class LLMServiceError(AppException):
    """LLM service related errors"""
    pass

class SessionNotFoundError(AppException):
    """Session not found in storage"""
    pass

class ValidationError(AppException):
    """Data validation errors"""
    pass

class ExternalServiceError(AppException):
    """External service (Redis, AWS) errors"""
    pass

class RateLimitExceeded(AppException):
    """Rate limit exceeded for session"""
    pass