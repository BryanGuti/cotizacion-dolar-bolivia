
import re
from datetime import datetime

import requests

from scraper.sources.base import build_quote


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
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

RATE_PATTERN = re.compile(
    r"Dólar\s+Compra\s*:\s*([\d.,]+)"
    r".*?"
    r"Dólar\s+Venta\s*:\s*([\d.,]+)",
    re.IGNORECASE | re.DOTALL,
)


def scrape(entity: dict, source: dict) -> dict:
    """
    Retrieve USD buy and sell rates from Banco FIE's API.

    Args:
        entity: Entity configuration.
        source: Source configuration containing the API URL.

    Returns:
        A normalized quotation dictionary.

    Raises:
        requests.RequestException: If the HTTP request fails.
        ValueError: If the API response or quotation is invalid.
    """
    response = requests.post(
        source["url"],
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://www.bancofie.com.bo",
        },
        timeout=30,
    )

    response.raise_for_status()

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise ValueError(
            "Banco FIE API returned an invalid JSON response."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "Banco FIE API response must be a JSON object."
        )

    if data.get("respuesta") is not True:
        raise ValueError(
            "Banco FIE API reported an unsuccessful response."
        )

    result = data.get("resultado")

    if not isinstance(result, dict):
        raise ValueError(
            "Banco FIE API response is missing the resultado object."
        )

    document = result.get("documento")
    raw_date = result.get("fecha")

    if not isinstance(document, str) or not document.strip():
        raise ValueError(
            "Banco FIE API response is missing the quotation document."
        )

    if not isinstance(raw_date, str) or not raw_date.strip():
        raise ValueError(
            "Banco FIE API response is missing the quotation date."
        )

    # Reject ambiguous quotations containing duplicated labels.
    buy_count = len(
        re.findall(r"Dólar\s+Compra\s*:", document, re.IGNORECASE)
    )
    sell_count = len(
        re.findall(r"Dólar\s+Venta\s*:", document, re.IGNORECASE)
    )

    if buy_count > 1:
        raise ValueError(
            "Multiple USD buy rates found in Banco FIE API response."
        )

    if sell_count > 1:
        raise ValueError(
            "Multiple USD sell rates found in Banco FIE API response."
        )

    match = RATE_PATTERN.search(document)

    if match is None:
        raise ValueError(
            "Could not extract USD buy and sell rates from Banco FIE."
        )

    quote_date = _parse_quote_date(raw_date)

    return build_quote(
        raw_buy=match.group(1),
        raw_sell=match.group(2),
        quote_date=quote_date,
    )


def _parse_quote_date(raw_date: str) -> str:
    match = re.fullmatch(
        r"\s*(\d{1,2})\s+de\s+([a-záéíóúñ]+)\s+(\d{4})\s*",
        raw_date.strip(),
        re.IGNORECASE,
    )

    if match is None:
        raise ValueError(
            f"Invalid Banco FIE quotation date: {raw_date}"
        )

    day = int(match.group(1))
    month_name = match.group(2).lower()
    year = int(match.group(3))

    month = MONTHS.get(month_name)

    if month is None:
        raise ValueError(
            f"Unknown month in Banco FIE quotation date: {month_name}"
        )

    try:
        return datetime(year, month, day).date().isoformat()
    except ValueError as exc:
        raise ValueError(
            f"Invalid Banco FIE quotation date: {raw_date}"
        ) from exc
