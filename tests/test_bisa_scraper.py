
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from scraper.sources.bisa import scrape


HTML = """
<section class="marquee-container">
    <p class="marquee-text">
        Tipos de cambio:
        <span><b>Dólar Compra </b>11,08</span> |
        <span><b>Dólar Venta </b>12,01</span> |
        <span><b>Euro Compra </b>11,336</span> |
        <span><b>Euro Venta </b>13,149</span> |
        <span><b>UFV </b>3,38047</span>
    </p>
</section>
"""

ENTITY = {
    "id": "bisa",
    "name": "Banco BISA",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bisa.com/home",
}


def mock_response(html=HTML):
    response = Mock()
    response.status_code = 200
    response.text = html
    response.raise_for_status.return_value = None
    return response


def test_scrape_returns_valid_quote(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("11.08")
    assert quote["sell"] == Decimal("12.01")
    assert quote["date"]


def test_scrape_uses_configured_url(monkeypatch):
    mock_get = Mock(return_value=mock_response())

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert mock_get.call_args.args[0] == SOURCE["url"]


def test_scrape_rejects_missing_container(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response("<html></html>"),
    )

    with pytest.raises(ValueError, match="exchange rate section"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_buy_rate(monkeypatch):
    html = """
    <section class="marquee-container">
        <span><b>Dólar Venta </b>12,01</span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Incomplete USD quotation"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    html = """
    <section class="marquee-container">
        <span><b>Dólar Compra </b>11,08</span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Incomplete USD quotation"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_empty_buy_rate(monkeypatch):
    html = """
    <section class="marquee-container">
        <span><b>Dólar Compra </b></span>
        <span><b>Dólar Venta </b>12,01</span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Missing value"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise requests.exceptions.HTTPError("HTTP error")

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        raise_http_error,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)


def test_scrape_handles_whitespace_after_label(monkeypatch):
    html = """
    <section class="marquee-container">
        <span>
            <b>Dólar Compra</b>

            <strong>11,08</strong>
        </span>
        <span>
            <b>Dólar Venta</b>

            <strong>12,01</strong>
        </span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("11.08")
    assert quote["sell"] == Decimal("12.01")


def test_scrape_rejects_duplicate_buy_rate(monkeypatch):
    html = """
    <section class="marquee-container">
        <span><b>Dólar Compra</b>11,08</span>
        <span><b>Dólar Compra</b>11,10</span>
        <span><b>Dólar Venta</b>12,01</span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Multiple values"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_duplicate_sell_rate(monkeypatch):
    html = """
    <section class="marquee-container">
        <span><b>Dólar Compra</b>11,08</span>
        <span><b>Dólar Venta</b>12,01</span>
        <span><b>Dólar Venta</b>12,05</span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Multiple values"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_buy_rate(monkeypatch):
    html = """
    <section class="marquee-container">
        <span><b>Dólar Compra</b>invalid</span>
        <span><b>Dólar Venta</b>12,01</span>
    </section>
    """

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Invalid value"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_connection_error(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("Connection failed")

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        raise_connection_error,
    )

    with pytest.raises(requests.ConnectionError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_timeout_error(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr(
        "scraper.sources.bisa.requests.get",
        raise_timeout,
    )

    with pytest.raises(requests.Timeout):
        scrape(ENTITY, SOURCE)
