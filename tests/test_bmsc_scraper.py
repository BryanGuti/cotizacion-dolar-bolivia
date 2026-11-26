
from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from scraper.sources import bmsc


@pytest.fixture
def entity():
    return {
        "id": "bmsc",
        "name": "Banco Mercantil Santa Cruz",
    }


@pytest.fixture
def source():
    return {
        "url": "https://backportal.bmsc.com.bo:1443/api/bmscservices/tipotre",
    }


def mock_response(data):
    response = Mock()
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def test_scrape_returns_buy_and_sell_rates(
    entity, source, monkeypatch
):
    response = mock_response({
        "compra": 10.65,
        "venta": 12.05,
        "oficial": 11.75,
    })

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    monkeypatch.setattr(
        bmsc,
        "_get_local_date",
        lambda: "2026-11-23",
    )

    quote = bmsc.scrape(entity, source)

    assert quote["date"] == "2026-11-23"
    assert quote["buy"] == Decimal("10.65")
    assert quote["sell"] == Decimal("12.05")
    assert "official_rate" not in quote

    response.raise_for_status.assert_called_once()


def test_scrape_sends_correct_request(entity, source, monkeypatch):
    response = mock_response({
        "compra": 10.65,
        "venta": 12.05,
    })

    get_mock = Mock(return_value=response)

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        get_mock,
    )

    monkeypatch.setattr(
        bmsc,
        "_get_local_date",
        lambda: "2026-11-23",
    )

    bmsc.scrape(entity, source)

    get_mock.assert_called_once_with(
        source["url"],
        headers={
            "Accept": "application/json",
        },
        timeout=15,
    )


def test_scrape_rejects_non_json_response(
    entity, source, monkeypatch
):
    response = mock_response(None)

    response.json.side_effect = requests.exceptions.JSONDecodeError(
        "Invalid JSON",
        "invalid",
        0,
    )

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="invalid JSON"):
        bmsc.scrape(entity, source)


def test_scrape_rejects_non_dictionary_response(
    entity, source, monkeypatch
):
    response = mock_response([
        {"compra": 10.65, "venta": 12.05}
    ])

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="JSON object"):
        bmsc.scrape(entity, source)


def test_scrape_rejects_missing_buy_rate(
    entity, source, monkeypatch
):
    response = mock_response({
        "venta": 12.05,
    })

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="compra"):
        bmsc.scrape(entity, source)


def test_scrape_rejects_missing_sell_rate(
    entity, source, monkeypatch
):
    response = mock_response({
        "compra": 10.65,
    })

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="venta"):
        bmsc.scrape(entity, source)


@pytest.mark.parametrize("field", ["compra", "venta"])
def test_scrape_rejects_null_rates(
    entity, source, monkeypatch, field
):
    data = {
        "compra": 10.65,
        "venta": 12.05,
    }

    data[field] = None

    response = mock_response(data)

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="empty"):
        bmsc.scrape(entity, source)


@pytest.mark.parametrize("field", ["compra", "venta"])
def test_scrape_rejects_invalid_rates(
    entity, source, monkeypatch, field
):
    data = {
        "compra": 10.65,
        "venta": 12.05,
    }

    data[field] = "invalid"

    response = mock_response(data)

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError):
        bmsc.scrape(entity, source)


def test_scrape_propagates_http_errors(
    entity, source, monkeypatch
):
    response = Mock()

    response.raise_for_status.side_effect = requests.HTTPError(
        "HTTP 500"
    )

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(requests.HTTPError):
        bmsc.scrape(entity, source)


def test_scrape_propagates_connection_errors(
    entity, source, monkeypatch
):
    get_mock = Mock(
        side_effect=requests.ConnectionError(
            "Connection failed"
        )
    )

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        get_mock,
    )

    with pytest.raises(requests.ConnectionError):
        bmsc.scrape(entity, source)


@pytest.mark.parametrize(
    "field,value",
    [
        ("compra", 0),
        ("compra", -1),
        ("compra", True),
        ("venta", 0),
        ("venta", -1),
        ("venta", True),
    ],
)

def test_scrape_rejects_non_positive_or_boolean_rates(
    entity, source, monkeypatch, field, value
):
    data = {
        "compra": 10.65,
        "venta": 12.05,
    }

    data[field] = value

    response = mock_response(data)

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError):
        bmsc.scrape(entity, source)


def test_scrape_propagates_timeout_errors(
    entity, source, monkeypatch
):
    get_mock = Mock(
        side_effect=requests.Timeout("Request timed out")
    )

    monkeypatch.setattr(
        bmsc.requests,
        "get",
        get_mock,
    )

    with pytest.raises(requests.Timeout):
        bmsc.scrape(entity, source)
