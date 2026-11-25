
import pytest

from scraper.config import SOURCES
from scraper.sources.bcb import scrape
from scraper.utils.validators import validate_quote


@pytest.mark.integration
def test_bcb_scraper_integration():
    entity = {
        "id": "bcb",
        "name": "Banco Central de Bolivia",
        "type": "central_bank",
    }

    quote = scrape(entity, SOURCES["bcb"])

    is_valid, errors = validate_quote(entity, quote)

    assert is_valid, errors
    assert quote["official_rate"] > 0

    print("\nBCB quotation:")
    print(f"Date: {quote['date']}")
    print(f"Official rate: {quote['official_rate']}")
    print(f"Captured at: {quote['captured_at']}")
