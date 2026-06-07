"""Domain-specific exception hierarchy for pipeline failure modes."""

class ScraperError(Exception):
    """Base class for scraper and orchestration errors."""
    pass

class NetworkError(ScraperError):
    """Raised when browser navigation or page interaction is unavailable."""
    pass

class CaptchaError(ScraperError):
    """Raised when anti-bot challenges block normal scraping."""
    pass

class ProductNotFound(ScraperError):
    """Raised when configured search strategies cannot resolve a product."""
    pass

class ConfigurationError(ScraperError):
    """Raised when required configuration is missing or malformed."""
    pass

class BrowserInitError(ScraperError):
    """Raised when the browser driver cannot be initialized."""
    pass

class DatabaseError(ScraperError):
    """Raised for database connectivity, queue, or write failures."""
    pass
