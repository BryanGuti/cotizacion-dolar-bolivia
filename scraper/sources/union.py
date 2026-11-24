
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from scraper.sources.base import build_quote


TIMEZONE = ZoneInfo("America/La_Paz")

RATE_PATTERN = re.compile(
    r"Dólar\s+Oficial\s*:\s*([\d.,]+)"
    r"\s*Compra\s+BOB\s*:\s*([\d.,]+)"
    r"\s*/\s*Venta\s*:\s*([\d.,]+)",
    re.IGNORECASE,
)


def scrape(entity: dict, source: dict) -> dict:
    """
    Retrieve USD buy and sell rates from Banco Unión.

    Args:
        entity: Entity configuration.
        source: Source configuration containing the website URL.

    Returns:
        A normalized quotation dictionary.

    Raises:
        requests.RequestException: If the HTTP request fails.
        ValueError: If the quotation cannot be found or parsed.
    """

    response = requests.get(
        source["url"],
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        },
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    elements = soup.select("p.card-text")

    matching_elements = []

    for element in elements:
        text = element.get_text(" ", strip=True)

        if "Dólar Oficial" not in text:
            continue

        match = RATE_PATTERN.search(text)

        if match:
            matching_elements.append(match)

    if not matching_elements:
        raise ValueError(
            "Could not find the USD quotation on Banco Unión's website."
        )

    if len(matching_elements) > 1:
        raise ValueError(
            "Multiple USD quotations found on Banco Unión's website."
        )

    match = matching_elements[0]

    raw_buy = match.group(2)
    raw_sell = match.group(3)

    quote_date = datetime.now(TIMEZONE).date().isoformat()

    return build_quote(
        raw_buy=raw_buy,
        raw_sell=raw_sell,
        quote_date=quote_date,
    )
