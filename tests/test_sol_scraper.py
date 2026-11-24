
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import pytest
import requests

from scraper.sources.sol import scrape


ENTITY = {
    "id": "sol",
    "name": "Banco Solidario",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bancosol.com.bo/",
}


HTML = """
<html>
<body>
    <span class="highlight-field">
        <p>
            <strong>Tipo de cambio oficial Boliviano por Dólar estadounidense</strong>:
            11.75
        </p>
        <p>
            <strong>Tipo de cambio compra:</strong> 10.58 -
            <strong>Tipo de cambio venta</strong>: 12.00
        </p>
    </span>

    <span class="highlight-field">
        Euro BCB: 12.8874 / Euro Compra-Venta: Consultar con Mesa de Dinero
    </span>

    <span class="highlight-field">
        UFV BCB: 3.37983
    </span>

    <span class="highlight-field">
        M.N. 3.78%
    </span>

    <span class="highlight-field">
        M.E. 0.50%
    </span>
</body>
</html>
"""


class MockResponse:
    def __init__(self, text=HTML, error=None):
        self.text = text
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error


def test_scrape_returns_valid_quote(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("10.58")
    assert quote["sell"] == Decimal("12.00")
    assert quote["date"] == datetime.now(
        ZoneInfo("America/La_Paz")
    ).date().isoformat()
    assert "captured_at" in quote


def test_scrape_uses_configured_url(monkeypatch):
    calls = []

    def mock_get(url, **kwargs):
        calls.append(url)
        return MockResponse()

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert calls == [SOURCE["url"]]


def test_scrape_uses_timeout(monkeypatch):
    captured = {}

    def mock_get(url, **kwargs):
        captured.update(kwargs)
        return MockResponse()

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert captured["timeout"] == 30


def test_scrape_rejects_missing_quotation_section(monkeypatch):
    html = """
    <span class="highlight-field">
        Euro BCB: 12.8874
    </span>
    """

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="quotation section was not found"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_buy_rate(monkeypatch):
    html = HTML.replace(
        "Tipo de cambio compra:</strong> 10.58",
        "Compra:</strong> 10.58",
    )

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="quotation section was not found"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    html = HTML.replace(
        "Tipo de cambio venta</strong>: 12.00",
        "Venta</strong>: 12.00",
    )

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="quotation section was not found"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_multiple_quotation_sections(monkeypatch):
    duplicate = """
    <span class="highlight-field">
        Tipo de cambio compra: 10.60
        Tipo de cambio venta: 12.10
    </span>
    """

    html = HTML.replace("</body>", duplicate + "</body>")

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple quotation sections"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_duplicate_buy_rates(monkeypatch):
    html = HTML.replace(
        "Tipo de cambio compra:</strong> 10.58",
        "Tipo de cambio compra:</strong> 10.58 - "
        "Tipo de cambio compra: 10.60",
    )

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple buy exchange rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(
            error=requests.exceptions.HTTPError("403 Forbidden")
        ),
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_duplicate_sell_rates(monkeypatch):
    html = HTML.replace(
        "Tipo de cambio venta</strong>: 12.00",
        "Tipo de cambio venta</strong>: 12.00 - "
        "Tipo de cambio venta: 12.10",
    )

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple sell exchange rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_connection_error(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("Connection failed")

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        raise_connection_error,
    )

    with pytest.raises(requests.ConnectionError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_timeout_error(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr(
        "scraper.sources.sol.requests.get",
        raise_timeout,
    )

    with pytest.raises(requests.Timeout):
        scrape(ENTITY, SOURCE)
