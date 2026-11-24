
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from scraper.sources.base import build_quote


TIMEZONE = ZoneInfo("America/La_Paz")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "es-BO,es;q=0.9,en;q=0.8",
    "Referer": "https://www.bg.com.bo/",
}


def scrape(entity: dict, source: dict) -> dict:
    response = requests.get(
        source["url"],
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(response.text, "html.parser")

    raw_buy = _extract_rate(
        soup,
        element_id="refCompra",
        expected_label="T. Cambio Compra",
    )

    raw_sell = _extract_rate(
        soup,
        element_id="refVenta",
        expected_label="T. Cambio Venta",
    )

    quote_date = datetime.now(TIMEZONE).date().isoformat()

    return build_quote(
        raw_buy=raw_buy,
        raw_sell=raw_sell,
        quote_date=quote_date,
    )


def _extract_rate(soup, element_id: str, expected_label: str) -> str:
    elements = soup.find_all(id=element_id)

    if not elements:
        raise ValueError(
            f"Banco Ganadero is missing the {element_id} element."
        )

    if len(elements) != 1:
        raise ValueError(
            f"Banco Ganadero returned multiple {element_id} elements."
        )

    element = elements[0]

    rate_pattern = re.compile(
        re.escape(expected_label)
        + r"\s*([\d.,]+)\s*Bs\.?",
        re.IGNORECASE,
    )

    for parent in element.parents:
        if parent.name != "div":
            continue

        text = parent.get_text(" ", strip=True)

        if expected_label.lower() not in text.lower():
            continue

        matches = rate_pattern.findall(text)

        if len(matches) == 1:
            return matches[0]

        if len(matches) > 1:
            raise ValueError(
                f"Banco Ganadero returned multiple rates for {expected_label}."
            )

    raise ValueError(
        f"Could not extract the rate for {expected_label}."
    )
