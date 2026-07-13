class AppError(Exception):
    """Base domain error."""
    
class ConfigurationError(AppError):
    """Invalid or missing configuration."""

class IntegrationError(AppError):
    """External integration failure."""