
from decimal import Decimal

import pytest
import requests

from scraper.sources.fortaleza import scrape


ENTITY = {
    "id": "fortaleza",
    "name": "Banco Fortaleza",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.bancofortaleza.com.bo/proxy-exchange.php",
    "method": "requests",
}

BASE_URL = "https://www.bancofortaleza.com.bo/"


VALID_RESPONSE = {
    "statusCode": "MSPM-0000",
    "response": {
        "officialExchange": 11.75,
        "buyExchange": 11.45,
        "saleExchange": 12.05,
        "ufvExchange": 3.37983,
    },
    "errorDetail": None,
    "httpStatus": "OK",
    "rootCause": None,
    "validStatusCode": True,
}


class MockResponse:
    def __init__(self, json_data=None, error=None):
        self.json_data = json_data
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.json_data


class MockSession:
    def __init__(self, api_response=None, homepage_error=None):
        self.headers = {}
        self.calls = []

        self.homepage_response = MockResponse(
            error=homepage_error
        )

        self.api_response = api_response or MockResponse(
            VALID_RESPONSE
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def get(self, url, **kwargs):
        self.calls.append({
            "url": url,
            "kwargs": kwargs,
        })

        if url == BASE_URL:
            return self.homepage_response

        return self.api_response


def mock_session(monkeypatch, api_response=None, homepage_error=None):
    session = MockSession(
        api_response=api_response,
        homepage_error=homepage_error,
    )

    monkeypatch.setattr(
        "scraper.sources.fortaleza.requests.Session",
        lambda: session,
    )

    return session


def test_scrape_returns_valid_quote(monkeypatch):
    mock_session(monkeypatch)

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("11.45")
    assert quote["sell"] == Decimal("12.05")
    assert "date" in quote
    assert "captured_at" in quote


def test_scrape_uses_configured_url(monkeypatch):
    session = mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    assert session.calls[0]["url"] == BASE_URL
    assert session.calls[1]["url"] == SOURCE["url"]


def test_scrape_uses_timeout(monkeypatch):
    session = mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    assert session.calls[0]["kwargs"]["timeout"] == 30
    assert session.calls[1]["kwargs"]["timeout"] == 30


def test_scrape_visits_homepage_before_api(monkeypatch):
    session = mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    assert len(session.calls) == 2
    assert session.calls[0]["url"] == BASE_URL
    assert session.calls[1]["url"] == SOURCE["url"]


def test_scrape_rejects_invalid_json_structure(monkeypatch):
    mock_session(
        monkeypatch,
        api_response=MockResponse(["invalid"]),
    )

    with pytest.raises(ValueError, match="invalid JSON structure"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_status_code(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "statusCode": "ERROR",
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="unsuccessful status code"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_status_flag(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "validStatusCode": False,
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="invalid status"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_response(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "response": None,
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="missing the exchange rates"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_buy_rate(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "response": {
            "saleExchange": 12.05,
        },
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="missing the buy"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "response": {
            "buyExchange": 11.45,
        },
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="missing the sell"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_buy_rate(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "response": {
            **VALID_RESPONSE["response"],
            "buyExchange": None,
        },
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_sell_rate(monkeypatch):
    data = {
        **VALID_RESPONSE,
        "response": {
            **VALID_RESPONSE["response"],
            "saleExchange": None,
        },
    }

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_error(monkeypatch):
    mock_session(
        monkeypatch,
        api_response=MockResponse(
            error=requests.exceptions.HTTPError("HTTP 500")
        ),
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)


def test_scrape_sends_expected_headers(monkeypatch):
    session = mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    assert "Mozilla/5.0" in session.headers["User-Agent"]
    assert session.headers["Accept"] == "application/json"
    assert session.headers["Referer"] == BASE_URL
    assert session.headers["Cache-Control"] == "no-cache"
    assert session.headers["Pragma"] == "no-cache"


def test_scrape_propagates_homepage_http_error(monkeypatch):
    mock_session(
        monkeypatch,
        homepage_error=requests.HTTPError("HTTP 403"),
    )

    with pytest.raises(requests.HTTPError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_connection_error(monkeypatch):
    class ErrorSession(MockSession):
        def get(self, url, **kwargs):
            raise requests.ConnectionError("Connection failed")

    session = ErrorSession()

    monkeypatch.setattr(
        "scraper.sources.fortaleza.requests.Session",
        lambda: session,
    )

    with pytest.raises(requests.ConnectionError):
        scrape(ENTITY, SOURCE)


def test_scrape_propagates_timeout_error(monkeypatch):
    class ErrorSession(MockSession):
        def get(self, url, **kwargs):
            raise requests.Timeout("Request timed out")

    session = ErrorSession()

    monkeypatch.setattr(
        "scraper.sources.fortaleza.requests.Session",
        lambda: session,
    )

    with pytest.raises(requests.Timeout):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_status_code(monkeypatch):
    data = {
        **VALID_RESPONSE,
    }
    data.pop("statusCode")

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="unsuccessful status code"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_valid_status_flag(monkeypatch):
    data = {
        **VALID_RESPONSE,
    }
    data.pop("validStatusCode")

    mock_session(
        monkeypatch,
        api_response=MockResponse(data),
    )

    with pytest.raises(ValueError, match="invalid status"):
        scrape(ENTITY, SOURCE)
