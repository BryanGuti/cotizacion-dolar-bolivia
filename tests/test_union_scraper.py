
from unittest.mock import Mock

import pytest
import requests

from scraper.sources import union


@pytest.fixture
def entity():
    return {
        "id": "union",
        "name": "Banco Unión",
    }


@pytest.fixture
def source():
    return {
        "url": "https://bancounion.com.bo/",
    }


def mock_response(html):
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None
    return response


def quotation_html():
    return """
    <html>
        <body>
            <p class="card-text">
                Dólar Oficial: 11,75
                <br>
                Compra BOB: 10,75 / Venta: 12,05
            </p>
        </body>
    </html>
    """


def test_scrape_returns_buy_and_sell_rates(
    entity, source, monkeypatch
):
    response = mock_response(quotation_html())

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    monkeypatch.setattr(
        union,
        "datetime",
        Mock(),
    )

    union.datetime.now.return_value.date.return_value.isoformat.return_value = (
        "2026-11-23"
    )

    quote = union.scrape(entity, source)

    assert quote["date"] == "2026-11-23"
    assert str(quote["buy"]) == "10.75"
    assert str(quote["sell"]) == "12.05"
    assert "official_rate" not in quote

    response.raise_for_status.assert_called_once()


def test_scrape_sends_correct_request(
    entity, source, monkeypatch
):
    response = mock_response(quotation_html())

    get_mock = Mock(return_value=response)

    monkeypatch.setattr(
        union.requests,
        "get",
        get_mock,
    )

    union.scrape(entity, source)

    get_mock.assert_called_once_with(
        source["url"],
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        },
        timeout=30,
    )


def test_scrape_finds_quotation_among_multiple_elements(
    entity, source, monkeypatch
):
    html = """
    <html>
        <body>
            <p class="card-text">Información general</p>
            <p class="card-text">Otra información</p>
            <p class="card-text">
                Dólar Oficial: 11,75
                <br>
                Compra BOB: 10,75 / Venta: 12,05
            </p>
            <p class="card-text">Información adicional</p>
        </body>
    </html>
    """

    response = mock_response(html)

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    quote = union.scrape(entity, source)

    assert str(quote["buy"]) == "10.75"
    assert str(quote["sell"]) == "12.05"


def test_scrape_rejects_missing_quotation(
    entity, source, monkeypatch
):
    html = """
    <html>
        <body>
            <p class="card-text">Información financiera</p>
        </body>
    </html>
    """

    response = mock_response(html)

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="Could not find"):
        union.scrape(entity, source)


def test_scrape_rejects_incomplete_quotation(
    entity, source, monkeypatch
):
    html = """
    <p class="card-text">
        Dólar Oficial: 11,75
        Compra BOB: 10,75
    </p>
    """

    response = mock_response(html)

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="Could not find"):
        union.scrape(entity, source)


def test_scrape_rejects_multiple_quotations(
    entity, source, monkeypatch
):
    html = """
    <html>
        <body>
            <p class="card-text">
                Dólar Oficial: 11,75
                Compra BOB: 10,75 / Venta: 12,05
            </p>
            <p class="card-text">
                Dólar Oficial: 11,75
                Compra BOB: 10,80 / Venta: 12,10
            </p>
        </body>
    </html>
    """

    response = mock_response(html)

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="Multiple"):
        union.scrape(entity, source)


@pytest.mark.parametrize(
    "html",
    [
        """
        <p class="card-text">
            Dólar Oficial: inválido
            Compra BOB: 10,75 / Venta: 12,05
        </p>
        """,
        """
        <p class="card-text">
            Dólar Oficial: 11,75
            Compra BOB: inválido / Venta: 12,05
        </p>
        """,
        """
        <p class="card-text">
            Dólar Oficial: 11,75
            Compra BOB: 10,75 / Venta: inválido
        </p>
        """,
    ],
)
def test_scrape_rejects_invalid_rates(
    entity, source, monkeypatch, html
):
    response = mock_response(html)

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(ValueError, match="Could not find"):
        union.scrape(entity, source)


def test_scrape_propagates_http_errors(
    entity, source, monkeypatch
):
    response = Mock()

    response.raise_for_status.side_effect = requests.HTTPError(
        "HTTP 500"
    )

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(requests.HTTPError):
        union.scrape(entity, source)


def test_scrape_propagates_connection_errors(
    entity, source, monkeypatch
):
    get_mock = Mock(
        side_effect=requests.ConnectionError(
            "Connection failed"
        )
    )

    monkeypatch.setattr(
        union.requests,
        "get",
        get_mock,
    )

    with pytest.raises(requests.ConnectionError):
        union.scrape(entity, source)


def test_scrape_uses_bolivia_timezone(
    entity, source, monkeypatch
):
    response = mock_response(quotation_html())

    datetime_mock = Mock()
    datetime_mock.now.return_value.date.return_value.isoformat.return_value = (
        "2026-11-24"
    )

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    monkeypatch.setattr(
        union,
        "datetime",
        datetime_mock,
    )

    quote = union.scrape(entity, source)

    assert quote["date"] == "2026-11-24"
    datetime_mock.now.assert_called_once_with(union.TIMEZONE)


def test_scrape_propagates_timeout_errors(
    entity, source, monkeypatch
):
    get_mock = Mock(
        side_effect=requests.Timeout("Request timed out")
    )

    monkeypatch.setattr(
        union.requests,
        "get",
        get_mock,
    )

    with pytest.raises(requests.Timeout):
        union.scrape(entity, source)


def test_scrape_rejects_quotation_with_invalid_buy_or_sell(
    entity, source, monkeypatch
):
    html = """
    <html>
        <body>
            <p class="card-text">
                Dólar Oficial: 11,75
                <br>
                Compra BOB: 10,75
            </p>
        </body>
    </html>
    """

    response = mock_response(html)

    monkeypatch.setattr(
        union.requests,
        "get",
        Mock(return_value=response),
    )

    with pytest.raises(
        ValueError,
        match="Could not find",
    ):
        union.scrape(entity, source)
