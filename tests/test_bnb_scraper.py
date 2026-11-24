from unittest.mock import Mock
from decimal import Decimal

import pytest
import requests

from scraper.sources.bnb import scrape


HTML = """
<div class="row">
    <div class="container d12">
        <div class="row">
            <div class="col-sm-12 text-center no-padding-lateral">
                <span>Tipos de Cambio</span>
                <span>Dólar Compra</span>
                <span>11.78</span>
                <span>Dólar Venta</span>
                <span>12.08</span>
                <span>Dólar Oficial</span>
                <span>11.78</span>
                <span>UFV</span>
                <span>3.38047</span>
            </div>
        </div>
    </div>
</div>
"""


ENTITY = {
    "id": "bnb",
    "name": "Banco Nacional de Bolivia",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bnb.com.bo/PortalBNB/Principal/BancaPersonas",
}


def mock_response(html=HTML):
    response = Mock()
    response.status_code = 200
    response.text = html
    response.raise_for_status.return_value = None
    return response


def test_scrape_returns_valid_quote(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        lambda *args, **kwargs: mock_response(),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("11.78")
    assert quote["sell"] == Decimal("12.08")
    assert quote["date"]


def test_scrape_uses_configured_url(monkeypatch):
    mock_get = Mock(return_value=mock_response())

    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        mock_get,
    )

    scrape(ENTITY, SOURCE)

    assert mock_get.call_args.args[0] == SOURCE["url"]


def test_scrape_rejects_missing_container(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        lambda *args, **kwargs: mock_response("<html></html>"),
    )

    with pytest.raises(ValueError, match="Could not find"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_buy_rate(monkeypatch):
    html = """
    <div class="container d12">
        <span>Tipos de Cambio</span>
        <span>Dólar Venta</span>
        <span>12.08</span>
    </div>
    """

    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Incomplete"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    html = """
    <div class="container d12">
        <span>Tipos de Cambio</span>
        <span>Dólar Compra</span>
        <span>11.78</span>
    </div>
    """

    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError, match="Incomplete"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_empty_buy_rate(monkeypatch):
    html = """
    <div class="container d12">
        <span>Tipos de Cambio</span>
        <span>Dólar Compra</span>
        <span></span>
        <span>Dólar Venta</span>
        <span>12.08</span>
    </div>
    """

    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        lambda *args, **kwargs: mock_response(html),
    )

    with pytest.raises(ValueError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise requests.exceptions.HTTPError("HTTP 500")

    monkeypatch.setattr(
        "scraper.sources.bnb.requests.get",
        raise_http_error,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)
