from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

SCRAPER_DIR = BASE_DIR / "scraper"
DOCS_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"

# Output files

CURRENT_DATA_FILE = DOCS_DIR / "data" / "current.json"
HISTORY_DIR = DATA_DIR / "history"

# Scraper execution state
PROGRESS_FILE = SCRAPER_DIR / "progress.json"

# Currency configuration
CURRENCY = "USD"
PRICE_CURRENCY = "BOB"

# Entities to scrape
ENTITIES = [
    {
        "id": "bcb",
        "name": "Banco Central de Bolivia",
        "type": "central_bank",
    },
    {
        "id": "bmsc",
        "name": "Banco Mercantil Santa Cruz",
        "type": "commercial_bank",
    },
    {
        "id": "union",
        "name": "Banco Unión",
        "type": "commercial_bank",
    },
    {
        "id": "bnb",
        "name": "Banco Nacional de Bolivia",
        "type": "commercial_bank",
    },
    {
        "id": "bisa",
        "name": "Banco BISA",
        "type": "commercial_bank",
    },
    {
        "id": "bcp",
        "name": "Banco de Crédito de Bolivia",
        "type": "commercial_bank",
    },
    {
        "id": "fie",
        "name": "Banco FIE",
        "type": "commercial_bank",
    },
    {
        "id": "ganadero",
        "name": "Banco Ganadero",
        "type": "commercial_bank",
    },
    {
        "id": "sol",
        "name": "Banco Solidario",
        "type": "commercial_bank",
    },
    {
        "id": "economico",
        "name": "Banco Económico",
        "type": "commercial_bank",
    },
    {
        "id": "fortaleza",
        "name": "Banco Fortaleza",
        "type": "commercial_bank",
    },
]

# Data sources
SOURCES = {
    "bcb": {
        # "url": "https://www.bcb.gob.bo/",
        "url": "https://www.bcb.gob.bo/librerias/indicadores/otras/ultimo.php",
        "method": "requests",
    },
    "bmsc": {
        # "url": "https://www.bmsc.com.bo/",
        "url": "https://backportal.bmsc.com.bo:1443/api/bmscservices/tipotre",
        "method": "requests",
    },
    "union": {
        "url": "https://bancounion.com.bo/",
        "method": "requests",
    },
    "bnb": {
        "url": "https://www.bnb.com.bo/PortalBNB/Principal/BancaPersonas",
        "method": "requests",
    },
    "bisa": {
        "url": "https://www.bisa.com/home",
        "method": "requests",
    },
    "bcp": {
        "url": "https://www.bcp.com.bo/",
        "method": "requests",
    },
    "fie": {
        # "url": "https://www.bancofie.com.bo/",
        "url": "https://www.bancofie.com.bo/api/tcl",
        "method": "requests",
    },
    "ganadero": {
        "url": "https://www.bg.com.bo/personas/",
        "method": "requests",
    },
    "sol": {
        "url": "https://www.bancosol.com.bo/",
        "method": "requests",
    },
    "economico": {
        "url": "https://www.baneco.com.bo/GetTipoCambio",
        "method": "requests",
    },
    "fortaleza": {
        "url": "https://www.bancofortaleza.com.bo/proxy-exchange.php",
        "method": "requests",
    },
}
