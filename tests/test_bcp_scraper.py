
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from scraper.sources.bcp import scrape


HTML = """
<div class="marquee-container">
    <div class="marquee-content">
        <span>Dólar Compra: 11.28</span>
        |
        <span>Dólar Venta: 12.08</span>
        |
        <span>UFV: 3.38047</span>
        |
        <span>USDT Venta: 11.95</span>
        |
        <span>USDT Compra: 11.75</span>
    </div>
</div>
"""

ENTITY = {
    "id": "bcp",
    "name": "Banco de Crédito de Bolivia",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bcp.com.bo/",
}


def mock_response(html=HTML):
    response = Mock()
    response.status_code = 200
    response.text = html
    response.raise_for_status.return_value = None
    return response


def test_scrape_returns_valid_quote(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        lambda *args, **kwargs: mock_response(),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("11.28")
    assert quote["sell"] == Decimal("12.08")
    assert quote["date"]


def test_scrape_uses_configured_url(monkeypatch):
    mock_get = Mock(return_value=mock_response())

    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert mock_get.call_args.args[0] == SOURCE["url"]


def test_scrape_rejects_missing_container(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        lambda *args, **kwargs: mock_response("<html></html>"),
    )

    with pytest.raises(ValueError, match="exchange rate section"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_buy_rate(monkeypatch):
    html = """
    <div class="marquee-container">
        <div class="marquee-content">
            <span>Dólar Venta: 12.08</span>
        </div>
    </div>
    """

    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Incomplete USD quotation"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    html = """
    <div class="marquee-container">
        <div class="marquee-content">
            <span>Dólar Compra: 11.28</span>
        </div>
    </div>
    """

    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Incomplete USD quotation"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_empty_buy_rate(monkeypatch):
    html = """
    <div class="marquee-container">
        <div class="marquee-content">
            <span>Dólar Compra:</span>
            <span>Dólar Venta: 12.08</span>
        </div>
    </div>
    """

    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Invalid value"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise requests.exceptions.HTTPError("HTTP error")

    monkeypatch.setattr(
        "scraper.sources.bcp.requests.get",
        raise_http_error,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)
