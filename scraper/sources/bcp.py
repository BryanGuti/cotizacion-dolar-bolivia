
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

    container = soup.select_one(
        ".marquee-container .marquee-content"
    )

    if container is None:
        raise ValueError(
            "Could not find the exchange rate section on BCP's website."
        )

    rates = {}

    for span in container.find_all("span"):
        text = span.get_text(" ", strip=True)

        if ":" not in text:
            continue

        label, raw_rate = text.split(":", 1)
        label = label.strip()
        raw_rate = raw_rate.strip()

        if label not in RATE_LABELS:
            continue

        if not RATE_PATTERN.fullmatch(raw_rate):
            raise ValueError(
                f"Invalid value for '{label}' on BCP's website: {raw_rate}"
            )

        rate_key = RATE_LABELS[label]

        if rate_key in rates:
            raise ValueError(
                f"Multiple values found for '{label}' on BCP's website."
            )

        rates[rate_key] = raw_rate

    if set(rates) != {"buy", "sell"}:
        raise ValueError(
            f"Incomplete USD quotation on BCP's website: {rates}"
        )

    return build_quote(
        raw_buy=rates["buy"],
        raw_sell=rates["sell"],
        quote_date=_get_local_date(),
    )


def _get_local_date() -> str:
    return datetime.now(TIMEZONE).date().isoformat()
