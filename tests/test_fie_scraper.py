
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from scraper.sources.fie import scrape


ENTITY = {
    "id": "fie",
    "name": "Banco FIE",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bancofie.com.bo/api/tcl",
}

DATA = {
    "respuesta": True,
    "hoy": "2026-11-24T04:00:00.579262Z",
    "resultado": {
        "documento": (
            "Dólar Oficial: 11,78 "
            "Dólar Compra: 10,78 "
            "Dólar Venta: 12,13 "
            "EURO BCB: 12,82842 "
            "UFV BOB: 3,38047"
        ),
        "fecha": "24 de noviembre 2026",
    },
}


def mock_response(data=DATA):
    response = Mock()
    response.status_code = 200
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def test_scrape_returns_valid_quote(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("10.78")
    assert quote["sell"] == Decimal("12.13")
    assert quote["date"] == "2026-11-24"


def test_scrape_uses_configured_url(monkeypatch):
    mock_post = Mock(return_value=mock_response())

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        mock_post,
    )

    scrape(ENTITY, SOURCE)

    assert mock_post.call_args.args[0] == SOURCE["url"]


def test_scrape_sends_expected_headers(monkeypatch):
    mock_post = Mock(return_value=mock_response())

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        mock_post,
    )

    scrape(ENTITY, SOURCE)

    headers = mock_post.call_args.kwargs["headers"]

    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"
    assert headers["Origin"] == "https://www.bancofie.com.bo"


def test_scrape_sends_no_payload(monkeypatch):
    mock_post = Mock(return_value=mock_response())

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        mock_post,
    )

    scrape(ENTITY, SOURCE)

    assert "json" not in mock_post.call_args.kwargs
    assert "data" not in mock_post.call_args.kwargs


def test_scrape_rejects_unsuccessful_response(monkeypatch):
    data = {"respuesta": False}

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="unsuccessful response"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_result(monkeypatch):
    data = {"respuesta": True}

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="resultado"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_rates(monkeypatch):
    data = {
        "respuesta": True,
        "resultado": {
            "documento": "Dólar Oficial: 11,78",
            "fecha": "24 de noviembre 2026",
        },
    }

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="Could not extract"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_date(monkeypatch):
    data = {
        "respuesta": True,
        "resultado": {
            "documento": (
                "Dólar Compra: 10,78 Dólar Venta: 12,13"
            ),
            "fecha": "fecha desconocida",
        },
    }

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="Invalid Banco FIE quotation date"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise requests.exceptions.HTTPError("HTTP error")

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        raise_http_error,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)


def test_scrape_handles_line_breaks_in_document(monkeypatch):
    data = {
        "respuesta": True,
        "resultado": {
            "documento": (
                "Dólar Oficial: 11,78\n"
                "Dólar Compra: 10,78\n"
                "Dólar Venta: 12,13\n"
            ),
            "fecha": "24 de noviembre 2026",
        },
    }

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("10.78")
    assert quote["sell"] == Decimal("12.13")


def test_scrape_rejects_duplicate_buy_rate(monkeypatch):
    data = {
        "respuesta": True,
        "resultado": {
            "documento": (
                "Dólar Compra: 10,78 "
                "Dólar Compra: 10,80 "
                "Dólar Venta: 12,13"
            ),
            "fecha": "24 de noviembre 2026",
        },
    }

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="Multiple USD buy rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_duplicate_sell_rate(monkeypatch):
    data = {
        "respuesta": True,
        "resultado": {
            "documento": (
                "Dólar Compra: 10,78 "
                "Dólar Venta: 12,13 "
                "Dólar Venta: 12,15"
            ),
            "fecha": "24 de noviembre 2026",
        },
    }

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="Multiple USD sell rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_non_dictionary_response(monkeypatch):
    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response([]),
    )

    with pytest.raises(ValueError, match="JSON object"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_json(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Invalid JSON",
        "invalid",
        0,
    )

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_result_type(monkeypatch):
    data = {
        "respuesta": True,
        "resultado": [],
    }

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        lambda *args, **kwargs: mock_response(data),
    )

    with pytest.raises(ValueError, match="resultado object"):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_connection_error(monkeypatch):
    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("Connection failed")

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        raise_connection_error,
    )

    with pytest.raises(requests.ConnectionError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_timeout_error(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr(
        "scraper.sources.fie.requests.post",
        raise_timeout,
    )

    with pytest.raises(requests.Timeout):
        scrape(ENTITY, SOURCE)
