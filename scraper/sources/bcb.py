
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from scraper.sources.base import build_official_quote


def scrape(entity: dict, source: dict) -> dict:
    """
    Extract the official USD exchange rate from the BCB website.
    """

    url = source["url"]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    rate_element = soup.select_one(
        ".tabla-cotizacion .fila1 .numero"
    )

    date_elements = soup.select(".encabezado .bcbs-subtitulo")

    if not date_elements:
        raise ValueError("Could not find the BCB quotation date.")

    date_element = date_elements[-1].select_one("div")

    if rate_element is None:
        raise ValueError("Could not find the BCB official exchange rate.")

    if date_element is None:
        raise ValueError("Could not find the BCB quotation date.")

    raw_rate = rate_element.get_text(strip=True)
    raw_date = date_element.get_text(" ", strip=True)

    date_match = re.search(
        r"(\d{1,2})\s+DE\s+"
        r"(ENERO|FEBRERO|MARZO|ABRIL|MAYO|JUNIO|"
        r"JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE)"
        r"\s+DE\s+(\d{4})",
        raw_date,
        flags=re.IGNORECASE,
    )

    if date_match is None:
        raise ValueError(
            f"Could not parse the BCB quotation date: {raw_date!r}"
        )

    months = {
        "ENERO": 1,
        "FEBRERO": 2,
        "MARZO": 3,
        "ABRIL": 4,
        "MAYO": 5,
        "JUNIO": 6,
        "JULIO": 7,
        "AGOSTO": 8,
        "SEPTIEMBRE": 9,
        "OCTUBRE": 10,
        "NOVIEMBRE": 11,
        "DICIEMBRE": 12,
    }

    day = int(date_match.group(1))
    month = months[date_match.group(2).upper()]
    year = int(date_match.group(3))

    quote_date = datetime(
        year,
        month,
        day,
    ).date().isoformat()

    return build_official_quote(
        raw_rate=raw_rate,
        quote_date=quote_date,
    )
