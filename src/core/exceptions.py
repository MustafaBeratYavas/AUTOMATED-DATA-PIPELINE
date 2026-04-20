# -- Domain-Specific Exception Hierarchy --
# Provides a structured exception taxonomy rooted in ScraperError.
# Each subclass maps to a distinct failure domain within the pipeline,
# enabling granular error handling and retry logic in upstream callers.

class ScraperError(Exception):
    # Base exception for all scraper-related failures
    pass

class NetworkError(ScraperError):
    # Raised on HTTP timeouts, connection resets, or DNS resolution failures
    pass

class CaptchaError(ScraperError):
    # Raised when anti-bot CAPTCHA challenges cannot be bypassed
    pass

class ProductNotFound(ScraperError):
    # Raised when neither internal nor fallback search yields a valid product page
    pass

class ConfigurationError(ScraperError):
    # Raised on missing or malformed entries in settings.yaml
    pass

class BrowserInitError(ScraperError):
    # Raised when the WebDriver/Chrome instance fails to initialise
    pass

class DatabaseError(ScraperError):
    # Raised on SQLite write failures, constraint violations, or lock contention
    pass
