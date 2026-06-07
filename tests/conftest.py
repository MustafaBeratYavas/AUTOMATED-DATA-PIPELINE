"""Shared pytest fixtures for scraper service unit tests."""

import pytest
from unittest.mock import MagicMock
from src.models.product import ProductDTO
from src.core.config import Config

@pytest.fixture
def mock_driver():
    """Return a minimal WebDriver mock with a stable starting page."""
    driver = MagicMock()
    driver.current_url = "https://www.akakce.com"
    driver.page_source = "<html></html>"
    return driver

@pytest.fixture
def mock_config():
    """Return a Config-like mock that defaults to empty selector mappings."""
    config = MagicMock(spec=Config)
    config.get.return_value = {}
    return config

@pytest.fixture
def sample_dto():
    """Return a representative DTO with brand and URL already populated."""
    return ProductDTO(
        code="TEST-001",
        brand="Razer",
        url="https://www.akakce.com/test-product.html",
    )

@pytest.fixture
def empty_dto():
    """Return a DTO containing only a product code."""
    return ProductDTO(code="EMPTY-001")
