from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"

# Output files

CURRENT_DATA_FILE = FRONTEND_DIR / "data" / "current.json"
HISTORY_DIR = FRONTEND_DIR / "data" / "history"

# Currency configuration
CURRENCY = "USD"
PRICE_CURRENCY = "BOB"

# Transient scraper failures are retried using these delays plus bounded jitter.
SCRAPE_RETRY_DELAYS_SECONDS = (3, 7, 15, 30)
SCRAPE_RETRY_JITTER_SECONDS = 1.0

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
        "url": "https://www.bcb.gob.bo/librerias/indicadores/otras/ultimo.php",
    },
    "bmsc": {
        "url": "https://backportal.bmsc.com.bo:1443/api/bmscservices/tipotre",
    },
    "union": {
        "url": "https://bancounion.com.bo/",
    },
    "bnb": {
        "url": "https://www.bnb.com.bo/PortalBNB/Principal/BancaPersonas",
    },
    "bisa": {
        "url": "https://www.bisa.com/home",
    },
    "bcp": {
        "url": "https://www.bcp.com.bo/",
    },
    "fie": {
        "url": "https://www.bancofie.com.bo/api/tcl",
    },
    "ganadero": {
        "url": "https://www.bg.com.bo/personas/",
    },
    "sol": {
        "url": "https://www.bancosol.com.bo/",
    },
    "economico": {
        "url": "https://www.baneco.com.bo/GetTipoCambio",
    },
    "fortaleza": {
        "url": "https://www.bancofortaleza.com.bo/proxy-exchange.php",
    },
}
