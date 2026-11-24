
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal

import pytest
import requests

from scraper.sources.ganadero import scrape


ENTITY = {
    "id": "ganadero",
    "name": "Banco Ganadero",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bg.com.bo/personas/",
}


HTML = """
<div>
    <div class="flex flex-row items-center w-1/4">
        <div class="hidden xl:block">
            <img id="dcompra" alt="T. Cambio Oficial">
        </div>
        <div>
            <div>T. Cambio Oficial</div>
            <div>11,78 Bs.</div>
        </div>
    </div>

    <div class="flex flex-row items-center w-1/4">
        <div class="hidden xl:block">
            <img id="refVenta" alt="T. Cambio Venta">
        </div>
        <div>
            <div>T. Cambio Venta</div>
            <div>12,08 Bs.</div>
        </div>
    </div>

    <div class="flex flex-row items-center w-1/4">
        <div class="hidden xl:block">
            <img id="refCompra" alt="T. Cambio Compra">
        </div>
        <div>
            <div>T. Cambio Compra</div>
            <div>10,00 Bs.</div>
        </div>
    </div>
</div>
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
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("10.00")
    assert quote["sell"] == Decimal("12.08")
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
        "scraper.sources.ganadero.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert calls == [SOURCE["url"]]


def test_scrape_sends_expected_headers(monkeypatch):
    captured = {}

    def mock_get(url, **kwargs):
        captured.update(kwargs)
        return MockResponse()

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert "Mozilla/5.0" in captured["headers"]["User-Agent"]
    assert captured["headers"]["Referer"] == "https://www.bg.com.bo/"
    assert captured["timeout"] == 30


def test_scrape_rejects_missing_buy_element(monkeypatch):
    html = HTML.replace('id="refCompra"', 'id="missing"')

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="missing the refCompra"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_element(monkeypatch):
    html = HTML.replace('id="refVenta"', 'id="missing"')

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="missing the refVenta"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_buy_rate(monkeypatch):
    html = HTML.replace("10,00 Bs.", "valor inválido")

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="Could not extract"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_duplicate_buy_elements(monkeypatch):
    html = HTML.replace(
        'id="refCompra"',
        'id="refCompra"',
        1,
    ) + '<img id="refCompra">'

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple refCompra"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(
            error=requests.exceptions.HTTPError("403 Forbidden")
        ),
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)



def test_scrape_rejects_duplicate_sell_elements(monkeypatch):
    html = HTML + '<img id="refVenta">'

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple refVenta"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    html = HTML.replace("12,08 Bs.", "valor inválido")

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="Could not extract"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_multiple_buy_rates(monkeypatch):
    html = HTML.replace(
        "T. Cambio Compra",
        "T. Cambio Compra 10,00 Bs. T. Cambio Compra",
    )

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_multiple_sell_rates(monkeypatch):
    html = HTML.replace(
        "T. Cambio Venta",
        "T. Cambio Venta 12,08 Bs. T. Cambio Venta",
    )

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        lambda *args, **kwargs: MockResponse(text=html),
    )

    with pytest.raises(ValueError, match="multiple rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_connection_error(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("Connection failed")

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        raise_connection_error,
    )

    with pytest.raises(requests.ConnectionError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_timeout_error(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr(
        "scraper.sources.ganadero.requests.get",
        raise_timeout,
    )

    with pytest.raises(requests.Timeout):
        scrape(ENTITY, SOURCE)
