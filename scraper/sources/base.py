
from datetime import datetime
from zoneinfo import ZoneInfo

from scraper.utils.normalizer import normalize_rate


TIMEZONE = ZoneInfo("America/La_Paz")


def _capture_timestamp() -> str:
    """Return the current timestamp in Bolivia's timezone."""

    return datetime.now(TIMEZONE).isoformat()


def build_official_quote(
    raw_rate,
    quote_date: str,
) -> dict:
    """
    Build a normalized quotation for a central bank.

    Args:
        raw_rate: Official exchange rate extracted from the source.
        quote_date: Date associated with the published quotation.

    Returns:
        A dictionary containing official_rate, date and captured_at.
    """

    if not isinstance(quote_date, str) or not quote_date.strip():
        raise ValueError("Quotation date must be a non-empty string.")

    return {
        "date": quote_date,
        "captured_at": _capture_timestamp(),
        "official_rate": normalize_rate(raw_rate),
    }


def build_quote(
    raw_buy,
    raw_sell,
    quote_date: str,
) -> dict:
    """
    Build a normalized quotation for a commercial bank.

    Args:
        raw_buy: Original purchase rate extracted from the source.
        raw_sell: Original selling rate extracted from the source.
        quote_date: Date associated with the published quotation.

    Returns:
        A dictionary containing buy, sell, date and captured_at.
    """

    if not isinstance(quote_date, str) or not quote_date.strip():
        raise ValueError("Quotation date must be a non-empty string.")

    return {
        "date": quote_date,
        "captured_at": _capture_timestamp(),
        "buy": normalize_rate(raw_buy),
        "sell": normalize_rate(raw_sell),
    }
