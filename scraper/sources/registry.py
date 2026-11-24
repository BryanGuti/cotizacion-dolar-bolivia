
from importlib import import_module
from collections.abc import Callable


# Maps each entity ID to its scraper module.
#
# A bank should only be registered after its scraper module
# has been implemented.
SCRAPER_MODULES = {
    "bcb": "scraper.sources.bcb",
    "bmsc": "scraper.sources.bmsc",
    "union": "scraper.sources.union",
    "bnb": "scraper.sources.bnb",
    "bisa": "scraper.sources.bisa",
    "bcp": "scraper.sources.bcp",
    "fie": "scraper.sources.fie",
    "ganadero": "scraper.sources.ganadero",
    "sol": "scraper.sources.sol",
    "economico": "scraper.sources.economico",
    "fortaleza": "scraper.sources.fortaleza",
}


def has_scraper(entity_id: str) -> bool:
    """
    Check whether an entity has a registered scraper.

    Args:
        entity_id: Unique entity identifier from config.py.

    Returns:
        True if the entity has a registered scraper.
    """

    return entity_id in SCRAPER_MODULES


def get_scraper(entity_id: str) -> Callable:
    """
    Load and return the scrape() function for an entity.

    Args:
        entity_id: Unique entity identifier from config.py.

    Returns:
        The entity's scrape() function.

    Raises:
        KeyError: If the entity has no registered scraper.
        ImportError: If the scraper module cannot be imported.
        AttributeError: If the module does not expose scrape().
        TypeError: If scrape is not callable.
    """

    module_path = SCRAPER_MODULES.get(entity_id)

    if module_path is None:
        raise KeyError(
            f"No scraper registered for entity: {entity_id}"
        )

    module = import_module(module_path)

    scraper = getattr(module, "scrape", None)

    if scraper is None:
        raise AttributeError(
            f"Scraper module '{module_path}' does not expose scrape()."
        )

    if not callable(scraper):
        raise TypeError(
            f"'scrape' in module '{module_path}' is not callable."
        )

    return scraper
