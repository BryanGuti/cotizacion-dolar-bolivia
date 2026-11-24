
import re
import requests

from datetime import date
from zoneinfo import ZoneInfo

from scraper.sources.base import build_quote


TIMEZONE = ZoneInfo("America/La_Paz")

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

DATE_PATTERN = re.compile(
    r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
}


def scrape(entity: dict, source: dict) -> dict:
    base_url = "https://www.baneco.com.bo"

    with requests.Session() as session:
        session.headers.update(HEADERS)

        # Establish the session and obtain the required cookies.
        homepage = session.get(
            base_url + "/",
            timeout=30,
        )
        homepage.raise_for_status()

        # Retrieve exchange rates.
        response = session.get(
            source["url"],
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            raise ValueError(
                "Banco Económico returned an invalid JSON structure."
            )

        if "Compra" not in data:
            raise ValueError(
                "Banco Económico is missing the buy exchange rate."
            )

        if "Venta" not in data:
            raise ValueError(
                "Banco Económico is missing the sell exchange rate."
            )

        # Retrieve the quotation date.
        date_response = session.get(
            base_url + "/GetFecha",
            timeout=30,
        )
        date_response.raise_for_status()

        date_data = date_response.json()

        if not isinstance(date_data, dict):
            raise ValueError(
                "Banco Económico returned an invalid date structure."
            )

        if "fecha" not in date_data:
            raise ValueError(
                "Banco Económico is missing the quotation date."
            )

        quote_date = _parse_quote_date(date_data["fecha"])

    return build_quote(
        raw_buy=data["Compra"],
        raw_sell=data["Venta"],
        quote_date=quote_date,
    )


def _parse_quote_date(raw_date: str) -> str:
    if not isinstance(raw_date, str):
        raise ValueError(
            "Banco Económico returned an invalid quotation date."
        )

    match = DATE_PATTERN.search(raw_date.strip().lower())

    if not match:
        raise ValueError(
            "Banco Económico returned an unrecognized quotation date."
        )

    day = int(match.group(1))
    month_name = match.group(2)
    year = int(match.group(3))

    month = MONTHS.get(month_name)

    if month is None:
        raise ValueError(
            "Banco Económico returned an unrecognized month."
        )

    try:
        return date(year, month, day).isoformat()
    except ValueError as exc:
        raise ValueError(
            "Banco Económico returned an invalid calendar date."
        ) from exc
