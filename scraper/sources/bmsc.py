
import requests

from scraper.sources.base import build_quote


def scrape(entity: dict, source: dict) -> dict:
    """
    Retrieve USD buy and sell rates from Banco Mercantil Santa Cruz.

    Args:
        entity: Entity configuration.
        source: Source configuration containing the API URL.

    Returns:
        A normalized quotation dictionary.

    Raises:
        requests.RequestException: If the HTTP request fails.
        ValueError: If the API response is invalid or incomplete.
    """

    response = requests.get(
        source["url"],
        headers={
            "Accept": "application/json",
        },
        timeout=15,
    )

    response.raise_for_status()

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise ValueError(
            "BMSC API returned an invalid JSON response."
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "BMSC API response must be a JSON object."
        )

    if "compra" not in data or "venta" not in data:
        raise ValueError(
            "BMSC API response is missing 'compra' or 'venta'."
        )

    if data["compra"] is None or data["venta"] is None:
        raise ValueError(
            "BMSC API returned an empty buy or sell rate."
        )

    return build_quote(
        raw_buy=data["compra"],
        raw_sell=data["venta"],
        quote_date=entity.get("date") or _get_local_date(),
    )


def _get_local_date() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(
        ZoneInfo("America/La_Paz")
    ).date().isoformat()
