from unittest.mock import Mock, patch

import pytest
import requests

from scraper.sources.bcb import scrape


ENTITY = {
    "id": "bcb",
    "name": "Banco Central de Bolivia",
    "type": "central_bank",
}

SOURCE = {
    "url": "https://www.bcb.gob.bo/librerias/indicadores/otras/ultimo.php",
    "method": "requests",
}


def build_response(html: str) -> Mock:
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None
    return response


def test_scrape_extracts_official_rate_and_date():
    html = """
    <html>
        <body>
            <div class="encabezado">
                <div class="bcbs-subtitulo">
                    <div>
                        TABLA DE COTIZACIONES DEL 23 DE NOVIEMBRE DE 2026
                    </div>
                </div>
            </div>

            <table class="tabla-cotizacion">
                <tr class="fila1">
                    <td class="numero">11.75</td>
                </tr>
            </table>
        </body>
    </html>
    """

    with patch(
        "scraper.sources.bcb.requests.get",
        return_value=build_response(html),
    ):
        quote = scrape(ENTITY, SOURCE)

    assert quote["date"] == "2026-11-23"
    assert quote["official_rate"] == 11.75
    assert "captured_at" in quote


def test_scrape_rejects_missing_rate():
    html = """
    <html>
        <body>
            <div class="encabezado">
                <div class="bcbs-subtitulo">
                    <div>
                        TABLA DE COTIZACIONES DEL 23 DE NOVIEMBRE DE 2026
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

    with patch(
        "scraper.sources.bcb.requests.get",
        return_value=build_response(html),
    ):
        with pytest.raises(ValueError, match="official exchange rate"):
            scrape(ENTITY, SOURCE)


def test_scrape_rejects_missing_date():
    html = """
    <html>
        <body>
            <div class="encabezado">
                <div class="bcbs-subtitulo"></div>
            </div>

            <table class="tabla-cotizacion">
                <tr class="fila1">
                    <td class="numero">11.75</td>
                </tr>
            </table>
        </body>
    </html>
    """

    with patch(
        "scraper.sources.bcb.requests.get",
        return_value=build_response(html),
    ):
        with pytest.raises(ValueError, match="quotation date"):
            scrape(ENTITY, SOURCE)


def test_scrape_rejects_invalid_date():
    html = """
    <html>
        <body>
            <div class="encabezado">
                <div class="bcbs-subtitulo">
                    <div>FECHA NO DISPONIBLE</div>
                </div>
            </div>

            <table class="tabla-cotizacion">
                <tr class="fila1">
                    <td class="numero">11.75</td>
                </tr>
            </table>
        </body>
    </html>
    """

    with patch(
        "scraper.sources.bcb.requests.get",
        return_value=build_response(html),
    ):
        with pytest.raises(ValueError, match="Could not parse"):
            scrape(ENTITY, SOURCE)


def test_scrape_propagates_http_errors():
    import requests

    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError(
        "HTTP 500"
    )

    with patch(
        "scraper.sources.bcb.requests.get",
        return_value=response,
    ):
        with pytest.raises(requests.HTTPError):
            scrape(ENTITY, SOURCE)


def test_scrape_propagates_connection_errors():
    with patch(
        "scraper.sources.bcb.requests.get",
        side_effect=requests.ConnectionError("Connection failed"),
    ):
        with pytest.raises(requests.ConnectionError):
            scrape(ENTITY, SOURCE)


def test_scrape_propagates_timeout_errors():
    with patch(
        "scraper.sources.bcb.requests.get",
        side_effect=requests.Timeout("Request timed out"),
    ):
        with pytest.raises(requests.Timeout):
            scrape(ENTITY, SOURCE)


def test_scrape_rejects_impossible_calendar_date():
    html = """
    <html>
        <body>
            <div class="encabezado">
                <div class="bcbs-subtitulo">
                    <div>
                        TABLA DE COTIZACIONES DEL 31 DE FEBRERO DE 2026
                    </div>
                </div>
            </div>

            <table class="tabla-cotizacion">
                <tr class="fila1">
                    <td class="numero">11.75</td>
                </tr>
            </table>
        </body>
    </html>
    """

    with patch(
        "scraper.sources.bcb.requests.get",
        return_value=build_response(html),
    ):
        with pytest.raises(ValueError):
            scrape(ENTITY, SOURCE)

