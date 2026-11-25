
/* =========================================================
   1. CONFIGURATION
   ========================================================= */

const DATA_URL = "./data/current.json";


/* =========================================================
   2. DATA VALIDATION
   ========================================================= */

function isValidRate(value) {
    return (
        typeof value === "number" &&
        Number.isFinite(value) &&
        value > 0
    );
}


/* =========================================================
   3. DATA NORMALIZATION
   ========================================================= */

function normalizeEntity(entity) {
    if (!entity || typeof entity !== "object") {
        return null;
    }

    if (
        typeof entity.id !== "string" ||
        typeof entity.name !== "string" ||
        typeof entity.date !== "string"
    ) {
        return null;
    }

    if (entity.type === "central_bank") {
        if (!isValidRate(entity.official_rate)) {
            return null;
        }

        return {
            ...entity,
            official_rate: entity.official_rate
        };
    }

    if (entity.type === "commercial_bank") {
        if (
            !isValidRate(entity.buy) ||
            !isValidRate(entity.sell)
        ) {
            return null;
        }

        return {
            ...entity,
            buy: entity.buy,
            sell: entity.sell
        };
    }

    return null;
}


/* =========================================================
   4. DIFFERENCE CALCULATIONS
   ========================================================= */

function calculateDifferences(rate, officialRate) {
    const money = rate - officialRate;

    const percentage = (money / officialRate) * 100;

    return {
        money,
        percentage
    };
}


function enrichEntity(entity, officialRate) {
    const buyDifference = calculateDifferences(
        entity.buy,
        officialRate
    );

    const sellDifference = calculateDifferences(
        entity.sell,
        officialRate
    );

    return {
        ...entity,

        differences: {
            buy: buyDifference,
            sell: sellDifference
        }
    };
}


/* =========================================================
   5. DATA PROCESSING
   ========================================================= */

function processDashboardData(rawData) {
    if (
        !rawData ||
        typeof rawData !== "object" ||
        !Array.isArray(rawData.entities)
    ) {
        throw new Error(
            "La estructura de current.json no es válida."
        );
    }

    const normalizedEntities = rawData.entities
        .map(normalizeEntity)
        .filter(Boolean);

    const officialEntity = normalizedEntities.find(
        entity => entity.type === "central_bank"
    );

    if (!officialEntity) {
        throw new Error(
            "No se encontró una cotización válida del BCB."
        );
    }

    const commercialEntities = normalizedEntities
        .filter(entity => entity.type === "commercial_bank")
        .map(entity =>
            enrichEntity(
                entity,
                officialEntity.official_rate
            )
        );

    return {
        updatedAt: rawData.updated_at ?? null,

        official: officialEntity,

        entities: commercialEntities
    };
}


/* =========================================================
   6. ENTITY SORTING
   ========================================================= */

function sortEntities(entities, operation) {
    const sortedEntities = [...entities];

    if (operation === "buy") {
        // Comprar USD:
        // The lowest selling rate is the best option.

        sortedEntities.sort(
            (a, b) => a.sell - b.sell
        );

    } else if (operation === "sell") {
        // Vender USD:
        // The highest buying rate is the best option.

        sortedEntities.sort(
            (a, b) => b.buy - a.buy
        );
    }

    return sortedEntities;
}


/* =========================================================
   7. DATA LOADING
   ========================================================= */

async function loadDashboardData() {
    const response = await fetch(DATA_URL, {
        cache: "no-cache"
    });

    if (!response.ok) {
        throw new Error(
            `No se pudieron cargar las cotizaciones. HTTP ${response.status}`
        );
    }

    const rawData = await response.json();

    return processDashboardData(rawData);
}


const HISTORY_START_YEAR = 2026;

function normalizeHistoryRecord(record, entityId) {
    if (!record || typeof record !== "object") {
        return null;
    }

    if (record.id !== entityId) {
        return null;
    }

    if (
        typeof record.date !== "string" ||
        !/^\d{4}-\d{2}-\d{2}$/.test(record.date)
    ) {
        return null;
    }

    if (entityId === "bcb") {
        if (!isValidRate(record.official_rate)) {
            return null;
        }

        return {
            date: record.date,
            capturedAt: record.captured_at ?? null,
            id: record.id,
            name: record.name,
            type: record.type,
            officialRate: record.official_rate,
        };
    }

    if (record.type === "commercial_bank") {
        if (
            !isValidRate(record.buy) ||
            !isValidRate(record.sell)
        ) {
            return null;
        }

        return {
            date: record.date,
            capturedAt: record.captured_at ?? null,
            id: record.id,
            name: record.name,
            type: record.type,
            buy: record.buy,
            sell: record.sell,
        };
    }

    return null;
}

function parseHistoryJSONL(content, entityId) {
    return content
        .split("\n")
        .filter(line => line.trim() !== "")
        .map(line => {
            try {
                return JSON.parse(line);
            } catch {
                return null;
            }
        })
        .map(record => normalizeHistoryRecord(record, entityId))
        .filter(Boolean);
}

async function loadHistoryYear(entityId, year) {
    const url = `/data/history/${year}/${entityId}.jsonl`;

    const response = await fetch(url, {
        cache: "no-cache",
    });

    if (response.status === 404) {
        return [];
    }

    if (!response.ok) {
        throw new Error(
            `No se pudo cargar el historial de ${entityId} (${response.status}).`
        );
    }

    const content = await response.text();

    return parseHistoryJSONL(content, entityId);
}

async function loadEntityHistory(entityId) {
    if (
        typeof entityId !== "string" ||
        !/^[a-z0-9_-]+$/.test(entityId)
    ) {
        throw new Error("Identificador de entidad inválido.");
    }

    const currentYear = Number(
        new Intl.DateTimeFormat("en-US", {
            timeZone: "America/La_Paz",
            year: "numeric",
        }).format(new Date())
    );

    const years = [];

    for (
        let year = HISTORY_START_YEAR;
        year <= currentYear;
        year++
    ) {
        years.push(year);
    }

    const yearlyRecords = await Promise.all(
        years.map(year => loadHistoryYear(entityId, year))
    );

    return yearlyRecords
        .flat()
        .sort((a, b) => {
            const dateComparison = a.date.localeCompare(b.date);

            if (dateComparison !== 0) {
                return dateComparison;
            }

            return (a.capturedAt ?? "").localeCompare(
                b.capturedAt ?? ""
            );
        });
}


function getLatestRecordsByDate(records) {
    const latestRecords = new Map();

    for (const record of records) {
        const existingRecord = latestRecords.get(record.date);

        if (!existingRecord) {
            latestRecords.set(record.date, record);
            continue;
        }

        const existingTimestamp = existingRecord.capturedAt
            ? Date.parse(existingRecord.capturedAt)
            : 0;

        const currentTimestamp = record.capturedAt
            ? Date.parse(record.capturedAt)
            : 0;

        if (currentTimestamp >= existingTimestamp) {
            latestRecords.set(record.date, record);
        }
    }

    return latestRecords;
}

function buildHistorySeries(officialHistory, entityHistory) {
    const officialRecords = getLatestRecordsByDate(officialHistory);
    const entityRecords = getLatestRecordsByDate(entityHistory);

    const dates = [
        ...new Set([
            ...officialRecords.keys(),
            ...entityRecords.keys(),
        ]),
    ].sort();

    return dates.map(date => {
        const officialRecord = officialRecords.get(date);
        const entityRecord = entityRecords.get(date);

        const officialRate = officialRecord?.officialRate ?? null;
        const buy = entityRecord?.buy ?? null;
        const sell = entityRecord?.sell ?? null;

        let buyDifference = null;
        let sellDifference = null;

        if (officialRate !== null && buy !== null) {
            buyDifference = calculateDifferences(
                buy,
                officialRate
            );
        }

        if (officialRate !== null && sell !== null) {
            sellDifference = calculateDifferences(
                sell,
                officialRate
            );
        }

        return {
            date,
            officialRate,
            buy,
            sell,
            buyDifference,
            sellDifference,
        };
    });
}

async function loadEntityChartData(entityId) {
    if (entityId === "bcb") {
        throw new Error(
            "El BCB no puede utilizarse como entidad comercial."
        );
    }

    const [officialHistory, entityHistory] = await Promise.all([
        loadEntityHistory("bcb"),
        loadEntityHistory(entityId),
    ]);

    return buildHistorySeries(
        officialHistory,
        entityHistory
    );
}

/* =========================================================
   8. PUBLIC API
   ========================================================= */

window.DollarData = Object.freeze({
    loadDashboardData,
    sortEntities,
    loadEntityHistory,
    loadEntityChartData,
});