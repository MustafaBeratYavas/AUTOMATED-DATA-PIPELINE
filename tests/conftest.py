# -- Shared Test Fixtures --
# Provides reusable pytest fixtures for driver mocks, config stubs,
# and pre-built ProductDTO instances used across the test suite.

import pytest
from unittest.mock import MagicMock
from src.models.product import ProductDTO
from src.core.config import Config

@pytest.fixture
def mock_driver():
    # Stubbed Selenium WebDriver with default URL and page source
    driver = MagicMock()
    driver.current_url = "https://www.akakce.com"
    driver.page_source = "<html></html>"
    return driver

@pytest.fixture
def mock_config():
    # Config stub returning empty dicts by default for selector lookups
    config = MagicMock(spec=Config)
    config.get.return_value = {}
    return config

@pytest.fixture
def sample_dto():
    # Pre-populated DTO for tests that need a product with brand and URL set
    return ProductDTO(
        code="TEST-001",
        brand="Razer",
        url="https://www.akakce.com/test-product.html",
    )

@pytest.fixture
def empty_dto():
    # Minimal DTO with only a product code — no brand, URL, or sellers
    return ProductDTO(code="EMPTY-001")
