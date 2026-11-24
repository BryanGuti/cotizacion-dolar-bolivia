
import requests
from bs4 import BeautifulSoup

from scraper.sources.base import build_quote


def scrape(entity: dict, source: dict) -> dict:
    """
    Retrieve USD buy and sell rates from Banco Nacional de Bolivia.

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

    containers = soup.select("div.container.d12")

    # Find the container that contains the exact exchange rate title.
    container = next(
        (
            element
            for element in containers
            if element.find(
                "span",
                string=lambda text: (
                    text is not None
                    and text.strip() == "Tipos de Cambio"
                ),
            )
        ),
        None,
    )

    if container is None:
        raise ValueError(
            "Could not find the USD quotation section on BNB's website."
        )

    spans = container.find_all("span")

    labels = {
        "Dólar Compra": "buy",
        "Dólar Venta": "sell",
    }

    rates = {}

    for index, span in enumerate(spans):
        label = span.get_text(" ", strip=True)

        if label not in labels:
            continue

        rate_type = labels[label]

        if rate_type in rates:
            raise ValueError(
                f"Multiple '{label}' values found on BNB's website."
            )

        if index + 1 >= len(spans):
            raise ValueError(
                f"Missing value for '{label}' on BNB's website."
            )

        raw_rate = spans[index + 1].get_text(" ", strip=True)

        if raw_rate in labels:
            raise ValueError(
                f"Missing value for '{label}' on BNB's website."
            )

        rates[rate_type] = raw_rate

    if set(rates) != {"buy", "sell"}:
        raise ValueError(
            f"Incomplete USD quotation on BNB's website: {rates}"
        )

    return build_quote(
        raw_buy=rates["buy"],
        raw_sell=rates["sell"],
        quote_date=_get_local_date(),
    )


def _get_local_date() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(
        ZoneInfo("America/La_Paz")
    ).date().isoformat()
