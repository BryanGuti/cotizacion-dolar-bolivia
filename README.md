# Dólar Bolivia

**Información y comparación de las cotizaciones del dólar estadounidense en Bolivia.**

Dólar Bolivia es un proyecto de software desarrollado para recopilar, procesar, validar y organizar información sobre las cotizaciones del dólar estadounidense (USD) publicadas por el Banco Central de Bolivia y distintas entidades financieras del país.

Su propósito es brindar información clara y estructurada sobre las cotizaciones disponibles para que las personas puedan consultar, comparar y tomar decisiones económicas basadas en datos.

El proyecto utiliza Python para automatizar la recopilación de información desde diferentes fuentes, validar los datos obtenidos y almacenarlos en formatos estructurados que permiten mantener un registro de las cotizaciones.

---

## 1. Objetivos del proyecto

El proyecto busca:

- Centralizar información sobre las cotizaciones del dólar estadounidense de distintas entidades financieras de Bolivia.
- Facilitar la comparación de los tipos de cambio de compra y venta.
- Proporcionar información del tipo de cambio oficial publicado por el Banco Central de Bolivia.
- Automatizar la recopilación y actualización de cotizaciones.
- Mantener un registro histórico de los datos recopilados.
- Garantizar la integridad de la información mediante procesos de validación.
- Facilitar el acceso a información que permita tomar decisiones económicas basadas en datos.

## 2. Entidades financieras

El sistema contempla las siguientes entidades:

| Entidad | Identificador | Tipo de información |
|---|---|---|
| Banco Central de Bolivia | `bcb` | Tipo de cambio oficial |
| Banco Mercantil Santa Cruz | `bmsc` | Compra y venta |
| Banco Unión | `union` | Compra y venta |
| Banco Nacional de Bolivia | `bnb` | Compra y venta |
| Banco BISA | `bisa` | Compra y venta |
| Banco de Crédito de Bolivia | `bcp` | Compra y venta |
| Banco FIE | `fie` | Compra y venta |
| Banco Ganadero | `ganadero` | Compra y venta |
| BancoSol | `sol` | Compra y venta |
| Banco Económico | `economico` | Compra y venta |
| Banco Fortaleza | `fortaleza` | Compra y venta |

Las cotizaciones se organizan según el tipo de entidad:

- **Banco Central de Bolivia:** proporciona el tipo de cambio oficial mediante el campo `official_rate`.
- **Entidades financieras comerciales:** proporcionan cotizaciones de compra (`buy`) y venta (`sell`).

Esta distinción permite procesar y presentar correctamente información que no tiene exactamente la misma naturaleza.

## 3. Funcionamiento general

El proceso de recopilación sigue las siguientes etapas:

1. **Configuración:** el sistema carga las entidades financieras y las fuentes de información registradas.
2. **Extracción:** cada scraper obtiene información desde la fuente correspondiente mediante solicitudes HTTP.
3. **Procesamiento:** se extraen los valores necesarios y se convierten a una representación numérica normalizada.
4. **Validación:** se comprueba que la información tenga una estructura correcta, fechas válidas y cotizaciones numéricas positivas y finitas.
5. **Almacenamiento:** las cotizaciones válidas se guardan en el archivo de datos actuales y en el historial correspondiente.
6. **Seguimiento:** el sistema registra el resultado del procesamiento de cada entidad para gestionar ejecuciones posteriores.

Cada entidad dispone de un scraper independiente. Por ello, un problema al consultar una fuente no impide necesariamente que las demás entidades sean procesadas.

## 4. Arquitectura del proyecto

El proyecto utiliza una arquitectura modular que separa la extracción de información, el procesamiento, la validación, el almacenamiento y la ejecución general.

### Estructura de directorios

```text
dolar-bolivia/
│
├── frontend/
│   ├── index.html
│   ├── pages/
│   │   └── compare.html
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── app.js
│   │   ├── compare.js
│   │   └── data.js
│   └── data/
│       ├── current.json
│       └── history/
│           └── YYYY/
│               ├── bcb.jsonl
│               └── ...
│
├── scraper/
│   ├── main.py
│   ├── config.py
│   ├── diagnose_bcp.py
│   ├── validate_public_data.py
│   │
│   ├── sources/
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── bcb.py
│   │   ├── bmsc.py
│   │   ├── union.py
│   │   ├── bnb.py
│   │   ├── bisa.py
│   │   ├── bcp.py
│   │   ├── fie.py
│   │   ├── ganadero.py
│   │   ├── sol.py
│   │   ├── economico.py
│   │   └── fortaleza.py
│   │
│   └── utils/
│       ├── logger.py
│       ├── validators.py
│       ├── normalizer.py
│       └── storage.py
│
├── scripts/
│   └── update_exchange_rates.sh
│
├── tests/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy-pages.yml
│
├── .gitignore
├── README.md
└── requirements.txt
```

### Responsabilidades de los módulos

**`scraper/main.py`**

Es el punto de entrada del programa. Coordina la ejecución de los scrapers, gestiona los errores, valida las cotizaciones y controla el almacenamiento de los resultados.

**`scraper/config.py`**

Contiene la configuración general del proyecto, las entidades financieras, las fuentes de información y las rutas utilizadas para almacenar los datos.

**`scraper/diagnose_bcp.py`** y **`scraper/validate_public_data.py`**

Son utilidades operativas opcionales: una diagnostica la conexión con BCP y la otra comprueba la integridad de los archivos públicos y su historial. Se pueden ejecutar con `python -m scraper.diagnose_bcp` y `python -m scraper.validate_public_data`.

**`scraper/sources/`**

Contiene los scrapers individuales y los componentes relacionados con la extracción de información.

- `base.py`: proporciona funciones comunes para construir cotizaciones con una estructura uniforme.
- `registry.py`: administra el registro de scrapers disponibles.
- Los demás módulos implementan la extracción específica de cada entidad financiera.

**`scraper/utils/`**

Contiene las herramientas compartidas por el sistema.

- `logger.py`: configura los registros de ejecución y sus niveles de importancia.
- `validators.py`: verifica la estructura y validez de las cotizaciones.
- `normalizer.py`: normaliza los valores numéricos obtenidos desde las distintas fuentes.
- `storage.py`: administra la lectura y escritura de los datos actuales e históricos.

**`scripts/update_exchange_rates.sh`**

Activa `.venv` y ejecuta `python -m scraper.main`. Solo si detecta cambios en `frontend/data/` ejecuta el flujo Git; entonces agrega toda `frontend/`, crea un commit `Update Data (AAAA-MM-DD HH:MM:SS)` y hace push. Así también publica cambios manuales de HTML, CSS y JavaScript cuando coincide con una actualización de datos. El scraper registra `captured_at` y `updated_at`, por lo que esos cambios de timestamp también cuentan aunque las tasas sean iguales. Toda la salida estándar y de error de la ejecución, incluidos scraper y Git, se anexa a `logs/AAAA-MM-DD.log`, cuyos permisos quedan restringidos al usuario local. Cada ejecución queda delimitada por fecha, hora, PID y estado de salida. La carpeta `logs/` está excluida de Git.

**`.github/workflows/`**

`ci.yml` ejecuta los tests en pull requests y se reutiliza antes de publicar. `deploy-pages.yml` publica únicamente el frontend después de un push a la rama predeterminada; GitHub Actions no ejecuta el scraper.

**`tests/`**

Contiene las pruebas automatizadas destinadas a comprobar el comportamiento de los módulos, scrapers y componentes del sistema.

**`frontend/`**

Contiene los recursos del frontend estático y el archivo de datos utilizado para consultar las cotizaciones actuales.

- `js/compare.js` y `pages/compare.html`: permiten comparar entidades y abrir una comparación desde el detalle de una cotización.

**`frontend/data/history/`**

Almacena los registros históricos de las cotizaciones organizados por año y entidad financiera.

## 5. Tecnologías utilizadas

- **Python:** lenguaje principal del backend.
- **Requests:** realización de solicitudes HTTP.
- **Beautiful Soup:** análisis y extracción de información desde documentos HTML.
- **JSON:** formato utilizado para almacenar los datos actuales.
- **JSON Lines (JSONL):** formato utilizado para conservar el historial.
- **Pytest:** ejecución de pruebas automatizadas.
- **HTML, CSS y JavaScript:** tecnologías utilizadas para el frontend estático.

## 6. Requisitos

Para ejecutar el proyecto se necesita:

- Python 3.10 o superior.
- pip.
- Git.
- Conexión a Internet para consultar las fuentes de información.

## 7. Instalación

Clonar el repositorio:

```bash
git clone <URL_DEL_REPOSITORIO>
```

Ingresar al directorio:

```bash
cd dolar-bolivia
```

Crear un entorno virtual:

```bash
python -m venv .venv
```

Activar el entorno virtual.

En Linux:

```bash
source .venv/bin/activate
```

En Windows:

```powershell
.venv\Scripts\activate
```

Instalar las dependencias:

```bash
pip install -r requirements.txt
```

## 8. Ejecución

Para ejecutar el sistema desde el directorio raíz del proyecto:

```bash
python -m scraper.main
```

Durante la ejecución, el programa:

1. Carga la configuración.
2. Comprueba la disponibilidad de los scrapers registrados.
3. Consulta todas las entidades configuradas en cada ejecución, incluso si ya se obtuvo una cotización ese día.
4. Extrae y normaliza las cotizaciones.
5. Valida los resultados.
6. Guarda las cotizaciones válidas.
7. Registra el resultado de cada entidad.
8. Presenta un resumen de ejecución mediante el sistema de logs.

La ejecución requiere conexión a Internet para acceder a las fuentes externas.

Cada entidad conserva un único registro histórico por fecha. Si una ejecución posterior encuentra valores de compra, venta o cotización oficial distintos para esa fecha, reemplaza el registro de esa fecha y sincroniza `current.json` cuando corresponda.

Para ejecutar y publicar los datos desde el entorno virtual, utiliza:

```bash
bash scripts/update_exchange_rates.sh
```

El script solo inicia el flujo Git al detectar cambios en `frontend/data/`. En ese caso agrega toda la carpeta `frontend/`, para incluir también cambios manuales del sitio. No agrega los logs ni cambios fuera del frontend. Git debe tener configuradas credenciales que permitan hacer push.

## 9. Automation and deployment

The scraper runs on the local Linux computer through `scripts/update_exchange_rates.sh`; GitHub Actions does not run the scraper. The script activates `.venv` and executes `python -m scraper.main`. It starts the Git flow only when files under `frontend/data/` changed, then stages all of `frontend/` so manual HTML, CSS, and JavaScript edits are included too. The scraper updates `captured_at` and `updated_at`, so timestamp-only changes also trigger this flow even when rates are unchanged. All standard output and errors from the scraper and Git are appended to the ignored daily log `logs/YYYY-MM-DD.log`, with permissions restricted to the local user. Each run is marked with start and end timestamps, PID, and exit status.

To run every two hours starting at 01:17, add this entry with `crontab -e`. Ubuntu cron supports the `CRON_TZ` setting; if another cron implementation ignores it, set the computer's system timezone to `America/La_Paz` instead. See the [Ubuntu crontab manual](https://manpages.ubuntu.com/manpages/noble/man5/crontab.5.html).

```cron
CRON_TZ=America/La_Paz
17 1-23/2 * * * /path/to/cotizacion-dolar-bolivia/scripts/update_exchange_rates.sh
```

This runs at 01:17, 03:17, 05:17, 07:17, 09:17, 11:17, 13:17, 15:17, 17:17, 19:17, 21:17, and 23:17. Replace `/path/to/cotizacion-dolar-bolivia` with the absolute repository path. Cron runs the script in that existing local clone; it does not create another checkout. Keep the clone on the remote default branch with its upstream configured so `git push` updates that branch and triggers production deployment. Cron runs as the crontab owner with a minimal environment. The script uses `/run/user/<uid>/keyring/ssh` when cron does not provide `SSH_AUTH_SOCK`, allowing GNOME Keyring to provide the unlocked SSH key. Logs are written to the repository's ignored `logs/` directory.

The `CI` workflow runs tests on pull requests and is reused by `Deploy GitHub Pages`. A successful push to the default branch runs the tests and then publishes only `frontend/`; this includes pushes made by the local Bash scraper. Relative page, stylesheet, script, current-data, and history URLs resolve beneath a project site's repository base path. The three historical charts continue to load JSONL data from `frontend/data/history/`.

To enable publication, set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**. The deployment workflow uses `contents: read`, `pages: write`, and `id-token: write`; no personal token is stored in the repository.

## 10. Validación y normalización de datos

Las distintas fuentes pueden presentar sus cotizaciones en formatos diferentes. Por esta razón, el proyecto incorpora mecanismos comunes para normalizar y validar la información.

### Normalización

El módulo `normalizer.py` convierte los valores obtenidos en números decimales (`Decimal`), evitando depender directamente de los formatos particulares de cada fuente.

Entre otras cosas, contempla:

- Valores numéricos enteros y decimales.
- Cadenas numéricas con coma decimal.
- Etiquetas monetarias reconocidas.
- Rechazo de valores vacíos o malformados.
- Rechazo de valores nulos, booleanos, negativos o iguales a cero.
- Rechazo de valores no finitos.

### Validación

El módulo `validators.py` comprueba que cada cotización cumpla con la estructura esperada.

Entre los controles se encuentran:

- Existencia de los campos obligatorios.
- Compatibilidad entre el tipo de entidad y los campos de cotización.
- Validez de las fechas.
- Validez del timestamp de captura.
- Valores numéricos positivos y finitos.
- Rechazo de campos incompatibles con el tipo de entidad.

Una cotización que no supera las validaciones no se guarda como un nuevo resultado válido.

## 11. Sistema de almacenamiento

El proyecto mantiene dos niveles principales de almacenamiento.

### Cotizaciones actuales

El archivo:

```text
frontend/data/current.json
```

Contiene la información actual almacenada para las entidades financieras.

Este archivo permite que otros componentes del proyecto puedan consumir los datos sin tener que ejecutar nuevamente los scrapers.

El sistema conserva la última cotización válida disponible para cada entidad. Una cotización antigua no reemplaza a otra más reciente.

### Historial de cotizaciones

Los registros históricos se almacenan en:

```text
frontend/data/history/
```

La estructura se organiza por año y por identificador de entidad:

```text
frontend/data/history/
└── 2026/
    ├── bcb.jsonl
    ├── bmsc.jsonl
    ├── union.jsonl
    ├── bnb.jsonl
    ├── bisa.jsonl
    ├── bcp.jsonl
    ├── fie.jsonl
    ├── ganadero.jsonl
    ├── sol.jsonl
    ├── economico.jsonl
    └── fortaleza.jsonl
```

Cada archivo utiliza el formato JSON Lines (JSONL), donde cada línea representa un registro independiente.

Los registros se organizan por fecha de cotización. Si se actualiza una cotización correspondiente a una fecha que ya existe, el sistema reemplaza ese registro en lugar de generar duplicados para la misma entidad y fecha.

### Integridad del almacenamiento

El módulo `storage.py` incorpora mecanismos para:

- Crear automáticamente los directorios necesarios.
- Validar la estructura de los datos almacenados.
- Evitar registros históricos duplicados por fecha.
- Mantener ordenados los registros históricos.
- Evitar que una cotización antigua reemplace a una más reciente.
- Realizar escrituras atómicas para reducir el riesgo de archivos incompletos.
- Recuperar y sincronizar información entre el archivo actual y el historial.

## 12. Manejo de errores y registros

El proyecto incorpora un sistema de logs que permite identificar el estado de ejecución y los problemas encontrados.

Los niveles utilizados incluyen:

- `DEBUG`: información de diagnóstico.
- `INFO`: información general del proceso.
- `SUCCESS`: operaciones completadas correctamente.
- `WARNING`: situaciones que requieren atención, pero no necesariamente detienen el proceso.
- `ERROR`: errores durante la ejecución.

Los errores de extracción, conexión, respuestas HTTP, procesamiento de datos o almacenamiento se gestionan individualmente.

Esto permite que un fallo en una entidad no interrumpa automáticamente el procesamiento de las demás.

## 13. Pruebas automatizadas

El proyecto utiliza Pytest para comprobar el comportamiento de sus componentes.

Las pruebas cubren diferentes aspectos:

- Normalización de cotizaciones.
- Validación de estructuras y valores.
- Construcción de cotizaciones.
- Registro y recuperación de scrapers.
- Extracción de información de cada entidad.
- Respuestas HTTP y errores de conexión.
- Respuestas JSON inválidas o incompletas.
- Valores duplicados o incorrectos.
- Almacenamiento de cotizaciones actuales.
- Actualización del historial.
- Recuperación de datos.
- Orquestación y manejo de errores.

### Ejecutar todas las pruebas

Desde el directorio raíz:

```bash
python -m pytest -v
```

### Ejecutar las pruebas de un módulo específico

Por ejemplo:

```bash
python -m pytest tests/test_normalizer.py -v
```

Para ejecutar las pruebas de un scraper:

```bash
python -m pytest tests/test_bcb_scraper.py -v
```

La prueba de integración que consulta directamente el BCB depende de la disponibilidad de Internet y del servicio externo. Las pruebas marcadas `integration` se excluyen de la suite predeterminada para que CI sea reproducible.

Para ejecutar las pruebas de integración de forma explícita:

```bash
python -m pytest -v -m integration
```

## 14. Consideraciones y limitaciones

La información recopilada depende de las fuentes externas consultadas y de la disponibilidad de sus servicios.

Es importante considerar que:

- Las entidades financieras pueden modificar sus páginas, APIs o formatos de respuesta.
- Una fuente puede encontrarse temporalmente fuera de servicio.
- La disponibilidad de una cotización puede variar según el canal de atención, las condiciones de la entidad o el tipo de operación.
- Los valores publicados por las entidades pueden estar sujetos a cambios.
- La hora de captura no necesariamente representa la hora en que la entidad modificó originalmente su cotización.
- La información recopilada no garantiza que una operación pueda realizarse exactamente al valor publicado.

Por lo tanto, los datos deben utilizarse como referencia informativa y comparativa. Antes de realizar una operación cambiaria, se recomienda verificar las condiciones directamente con la entidad financiera correspondiente.

## 15. Estado del proyecto

El backend cuenta con scrapers implementados para once entidades, módulos comunes de procesamiento y almacenamiento, mecanismos de validación y recuperación, y pruebas automatizadas.

El proyecto está estructurado para facilitar la incorporación de nuevas fuentes de información y la evolución de sus componentes.

## 16. Licencia

La licencia del proyecto está pendiente de definición.

Hasta que se incorpore un archivo de licencia, no se debe asumir que el código está disponible para reutilización, modificación o distribución bajo una licencia de software libre.
