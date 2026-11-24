
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from scraper.sources.base import build_quote


TIMEZONE = ZoneInfo("America/La_Paz")

RATE_LABELS = {
    "Dólar Compra": "buy",
    "Dólar Venta": "sell",
}

RATE_PATTERN = re.compile(r"^\s*[\d.,]+\s*$")


def scrape(entity: dict, source: dict) -> dict:
    """
    Retrieve USD buy and sell rates from Banco BISA.

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

    container = soup.select_one("section.marquee-container")

    if container is None:
        raise ValueError(
            "Could not find the exchange rate section on BISA's website."
        )

    rates = {}

    for span in container.find_all("span"):
        label_element = span.find("b")

        if label_element is None:
            continue

        label = label_element.get_text(" ", strip=True)

        if label not in RATE_LABELS:
            continue

        rate_key = RATE_LABELS[label]

        if rate_key in rates:
            raise ValueError(
                f"Multiple values found for '{label}' on BISA's website."
            )

        # Find the first non-empty sibling after the label.
        raw_rate = None

        for sibling in label_element.next_siblings:
            value = (
                sibling.get_text(" ", strip=True)
                if hasattr(sibling, "get_text")
                else str(sibling).strip()
            )

            if value:
                raw_rate = value
                break

        if raw_rate is None:
            raise ValueError(
                f"Missing value for '{label}' on BISA's website."
            )

        if not RATE_PATTERN.fullmatch(raw_rate):
            raise ValueError(
                f"Invalid value for '{label}' on BISA's website: {raw_rate}"
            )

        rates[rate_key] = raw_rate

    if set(rates) != {"buy", "sell"}:
        raise ValueError(
            f"Incomplete USD quotation on BISA's website: {rates}"
        )

    return build_quote(
        raw_buy=rates["buy"],
        raw_sell=rates["sell"],
        quote_date=_get_local_date(),
    )


def _get_local_date() -> str:
    return datetime.now(TIMEZONE).date().isoformat()
