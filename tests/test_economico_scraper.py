
from decimal import Decimal

import pytest
import requests

from scraper.sources.economico import scrape, _parse_quote_date


ENTITY = {
    "id": "economico",
    "name": "Banco Económico",
    "type": "commercial_bank",
}

SOURCE = {
    "url": "https://www.baneco.com.bo/GetTipoCambio",
}

QUOTE_DATA = {
    "Oficial": 11.78,
    "Compra": 10.78,
    "Venta": 12.13,
    "UFV": 3.38047,
    "SueldoMinimo": 3499,
}

DATE_DATA = {
    "fecha": "Al Martes, 24 de Noviembre de 2026",
}


class MockResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class MockSession:
    def __init__(self, quote_data=None, date_data=None):
        self.headers = {}
        self.quote_data = (
            QUOTE_DATA if quote_data is None else quote_data
        )
        self.date_data = (
            DATE_DATA if date_data is None else date_data
        )
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))

        if url == "https://www.baneco.com.bo/":
            return MockResponse({})

        if url == SOURCE["url"]:
            return MockResponse(self.quote_data)

        if url == "https://www.baneco.com.bo/GetFecha":
            return MockResponse(self.date_data)

        raise ValueError(f"Unexpected URL: {url}")


def create_mock_session(monkeypatch, **kwargs):
    session = MockSession(**kwargs)

    monkeypatch.setattr(
        "scraper.sources.economico.requests.Session",
        lambda: session,
    )

    return session


def test_scrape_returns_valid_quote(monkeypatch):
    create_mock_session(monkeypatch)

    quote = scrape(ENTITY, SOURCE)

    assert quote["buy"] == Decimal("10.78")
    assert quote["sell"] == Decimal("12.13")
    assert quote["date"] == "2026-11-24"
    assert "captured_at" in quote


def test_scrape_uses_configured_url(monkeypatch):
    session = create_mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    urls = [call[0] for call in session.calls]

    assert SOURCE["url"] in urls


def test_scrape_uses_timeout(monkeypatch):
    session = create_mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    assert all(
        kwargs["timeout"] == 30
        for _, kwargs in session.calls
    )


def test_scrape_visits_homepage_before_api(monkeypatch):
    session = create_mock_session(monkeypatch)

    scrape(ENTITY, SOURCE)

    urls = [call[0] for call in session.calls]

    assert urls == [
        "https://www.baneco.com.bo/",
        SOURCE["url"],
        "https://www.baneco.com.bo/GetFecha",
    ]


def test_scrape_rejects_invalid_json_structure(monkeypatch):
    create_mock_session(
        monkeypatch,
        quote_data=["invalid"],
    )

    with pytest.raises(ValueError, match="invalid JSON structure"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_buy_rate(monkeypatch):
    create_mock_session(
        monkeypatch,
        quote_data={"Venta": 12.13},
    )

    with pytest.raises(ValueError, match="missing the buy"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_sell_rate(monkeypatch):
    create_mock_session(
        monkeypatch,
        quote_data={"Compra": 10.78},
    )

    with pytest.raises(ValueError, match="missing the sell"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_buy_rate(monkeypatch):
    create_mock_session(
        monkeypatch,
        quote_data={
            "Compra": None,
            "Venta": 12.13,
        },
    )

    with pytest.raises(ValueError):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_sell_rate(monkeypatch):
    create_mock_session(
        monkeypatch,
        quote_data={
            "Compra": 10.78,
            "Venta": None,
        },
    )

    with pytest.raises(ValueError):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_date(monkeypatch):
    create_mock_session(
        monkeypatch,
        date_data={},
    )

    with pytest.raises(ValueError, match="missing the quotation date"):
        scrape(ENTITY, SOURCE)


def test_parse_quote_date():
    assert _parse_quote_date(
        "Al Martes, 24 de Noviembre de 2026"
    ) == "2026-11-24"


def test_parse_quote_date_rejects_invalid_date():
    with pytest.raises(ValueError):
        _parse_quote_date("Fecha desconocida")


def test_scrape_propagates_http_error(monkeypatch):
    class ErrorSession(MockSession):
        def get(self, url, **kwargs):
            if url == "https://www.baneco.com.bo/":
                return MockResponse({})

            raise requests.exceptions.HTTPError("HTTP 500")

    session = ErrorSession()

    monkeypatch.setattr(
        "scraper.sources.economico.requests.Session",
        lambda: session,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_date_structure(monkeypatch):
    create_mock_session(
        monkeypatch,
        date_data=["invalid"],
    )

    with pytest.raises(ValueError, match="invalid date structure"):
        scrape(ENTITY, SOURCE)


def test_scrape_rejects_non_string_date(monkeypatch):
    create_mock_session(
        monkeypatch,
        date_data={"fecha": 20261124},
    )

    with pytest.raises(ValueError, match="invalid quotation date"):
        scrape(ENTITY, SOURCE)


def test_parse_quote_date_rejects_unknown_month():
    with pytest.raises(ValueError, match="unrecognized month"):
        _parse_quote_date("24 de MesDesconocido de 2026")


def test_parse_quote_date_rejects_invalid_calendar_date():
    with pytest.raises(ValueError, match="invalid calendar date"):
        _parse_quote_date("31 de febrero de 2026")


def test_parse_quote_date_accepts_setiembre():
    assert _parse_quote_date(
        "24 de setiembre de 2026"
    ) == "2026-09-24"


def test_scrape_propagates_connection_error(monkeypatch):
    class ErrorSession(MockSession):
        def get(self, url, **kwargs):
            raise requests.ConnectionError("Connection failed")

    session = ErrorSession()

    monkeypatch.setattr(
        "scraper.sources.economico.requests.Session",
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
        "scraper.sources.economico.requests.Session",
        lambda: session,
    )

    with pytest.raises(requests.Timeout):
        scrape(ENTITY, SOURCE)
