
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from scraper.sources.base import build_quote


TIMEZONE = ZoneInfo("America/La_Paz")

RATE_PATTERNS = {
    "buy": re.compile(
        r"Tipo\s+de\s+cambio\s+compra\s*:\s*([\d.,]+)",
        re.IGNORECASE,
    ),
    "sell": re.compile(
        r"Tipo\s+de\s+cambio\s+venta\s*:\s*([\d.,]+)",
        re.IGNORECASE,
    ),
}


def scrape(entity: dict, source: dict) -> dict:
    response = requests.get(
        source["url"],
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    elements = soup.select("span.highlight-field")

    candidates = []

    for element in elements:
        text = element.get_text(" ", strip=True)

        if (
            RATE_PATTERNS["buy"].search(text)
            and RATE_PATTERNS["sell"].search(text)
        ):
            candidates.append(text)

    if not candidates:
        raise ValueError(
            "BancoSol quotation section was not found."
        )

    if len(candidates) != 1:
        raise ValueError(
            "BancoSol returned multiple quotation sections."
        )

    text = candidates[0]

    raw_buy = _extract_rate(text, "buy")
    raw_sell = _extract_rate(text, "sell")

    quote_date = datetime.now(TIMEZONE).date().isoformat()

    return build_quote(
        raw_buy=raw_buy,
        raw_sell=raw_sell,
        quote_date=quote_date,
    )


def _extract_rate(text: str, rate_type: str) -> str:
    pattern = RATE_PATTERNS[rate_type]
    matches = pattern.findall(text)

    if not matches:
        raise ValueError(
            f"BancoSol is missing the {rate_type} exchange rate."
        )

    if len(matches) != 1:
        raise ValueError(
            f"BancoSol returned multiple {rate_type} exchange rates."
        )

    return matches[0]
