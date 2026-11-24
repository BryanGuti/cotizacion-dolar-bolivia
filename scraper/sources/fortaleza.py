
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from scraper.sources.base import build_quote


TIMEZONE = ZoneInfo("America/La_Paz")

BASE_URL = "https://www.bancofortaleza.com.bo/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/158.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def scrape(entity: dict, source: dict) -> dict:
    with requests.Session() as session:
        session.headers.update(HEADERS)

        # Establish a session and receive the required cookies.
        homepage = session.get(
            BASE_URL,
            timeout=30,
        )
        homepage.raise_for_status()

        # Request the exchange rates using the same session.
        response = session.get(
            source["url"],
            timeout=30,
        )
        response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError(
            "Banco Fortaleza returned an invalid JSON structure."
        )

    if data.get("statusCode") != "MSPM-0000":
        raise ValueError(
            "Banco Fortaleza returned an unsuccessful status code."
        )

    if data.get("validStatusCode") is not True:
        raise ValueError(
            "Banco Fortaleza returned an invalid status."
        )

    result = data.get("response")

    if not isinstance(result, dict):
        raise ValueError(
            "Banco Fortaleza is missing the exchange rates."
        )

    if "buyExchange" not in result:
        raise ValueError(
            "Banco Fortaleza is missing the buy exchange rate."
        )

    if "saleExchange" not in result:
        raise ValueError(
            "Banco Fortaleza is missing the sell exchange rate."
        )

    quote_date = datetime.now(TIMEZONE).date().isoformat()

    return build_quote(
        raw_buy=result["buyExchange"],
        raw_sell=result["saleExchange"],
        quote_date=quote_date,
    )
