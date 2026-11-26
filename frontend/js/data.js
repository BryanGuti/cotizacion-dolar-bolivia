
/* =========================================================
   1. CONFIGURATION
   ========================================================= */

const SCRIPT_DIRECTORY = new URL(".", document.currentScript.src);
const DATA_URL = new URL("../data/current.json", SCRIPT_DIRECTORY);
const HISTORY_DIRECTORY = new URL("../data/history/", SCRIPT_DIRECTORY);


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
    const availableEntities = entities.filter(
        entity => entity.quoteAvailable !== false
    );
    const unavailableEntities = entities.filter(
        entity => entity.quoteAvailable === false
    );

    if (operation === "buy") {
        // Comprar USD:
        // The lowest selling rate is the best option.

        availableEntities.sort(
            (a, b) => a.sell - b.sell
        );

    } else if (operation === "sell") {
        // Vender USD:
        // The highest buying rate is the best option.

        availableEntities.sort(
            (a, b) => b.buy - a.buy
        );
    }

    return [...availableEntities, ...unavailableEntities];
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
    const dashboardData = processDashboardData(rawData);
    const entityIds = [
        "bcb",
        ...dashboardData.entities.map(entity => entity.id),
    ];
    const historyEntries = await Promise.all(
        entityIds.map(async entityId => {
            try {
                return [entityId, await loadEntityHistory(entityId)];
            } catch (error) {
                console.warn(`No se pudo cargar el historial de ${entityId}:`, error);
                return [entityId, []];
            }
        })
    );
    const historyByEntity = Object.fromEntries(historyEntries);
    const officialHistory = historyByEntity.bcb;

    dashboardData.official.dailyChange = findDailyChange(
        dashboardData.official.official_rate,
        dashboardData.official.date,
        officialHistory,
        "officialRate"
    );
    dashboardData.entities = dashboardData.entities.map(entity => ({
        ...entity,
        quoteAvailable: true,
        dailyChanges: {
            buy: findDailyChange(
                entity.buy,
                entity.date,
                historyByEntity[entity.id],
                "buy"
            ),
            sell: findDailyChange(
                entity.sell,
                entity.date,
                historyByEntity[entity.id],
                "sell"
            ),
        },
    }));
    dashboardData.historyByEntity = historyByEntity;
    dashboardData.availableDates = [
        ...new Set([
            ...getLatestRecordsByDate(officialHistory).keys(),
            dashboardData.official.date,
        ]),
    ].sort();
    dashboardData.selectedDate = dashboardData.official.date;
    dashboardData.isHistorical = false;

    return dashboardData;
}


const HISTORY_START_YEAR = 2026;
const HISTORY_CACHE = new Map();

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
    const url = new URL(
        `${year}/${encodeURIComponent(entityId)}.jsonl`,
        HISTORY_DIRECTORY
    );

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

    if (HISTORY_CACHE.has(entityId)) {
        return HISTORY_CACHE.get(entityId);
    }

    const historyPromise = (async () => {
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
    })();

    HISTORY_CACHE.set(entityId, historyPromise);

    try {
        return await historyPromise;
    } catch (error) {
        HISTORY_CACHE.delete(entityId);
        throw error;
    }
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

function findDailyChange(currentRate, currentDate, history, rateKey) {
    if (!Array.isArray(history) || !currentDate) {
        return null;
    }

    const previousRecords = [...getLatestRecordsByDate(history).values()]
        .filter(record => record.date < currentDate)
        .sort((a, b) => a.date.localeCompare(b.date));
    const previousRecord = previousRecords[previousRecords.length - 1];

    if (!previousRecord || !isValidRate(previousRecord[rateKey])) {
        return null;
    }

    const money = currentRate - previousRecord[rateKey];

    return {
        money,
        percentage: (money / previousRecord[rateKey]) * 100,
        previousDate: previousRecord.date,
    };
}

function selectDashboardDate(dashboardData, date) {
    if (!dashboardData || typeof date !== "string") {
        return null;
    }

    const officialRecord = getLatestRecordsByDate(
        dashboardData.historyByEntity?.bcb ?? []
    ).get(date);

    if (!officialRecord) {
        return null;
    }

    const official = {
        date: officialRecord.date,
        captured_at: officialRecord.capturedAt,
        id: officialRecord.id,
        name: officialRecord.name,
        type: officialRecord.type,
        official_rate: officialRecord.officialRate,
        dailyChange: findDailyChange(
            officialRecord.officialRate,
            date,
            dashboardData.historyByEntity.bcb,
            "officialRate"
        ),
    };

    const entities = dashboardData.entities.map(currentEntity => {
        const record = getLatestRecordsByDate(
            dashboardData.historyByEntity[currentEntity.id] ?? []
        ).get(date);

        if (!record) {
            return {
                ...currentEntity,
                date,
                buy: null,
                sell: null,
                quoteAvailable: false,
                differences: null,
                dailyChanges: { buy: null, sell: null },
            };
        }

        const selectedEntity = {
            ...currentEntity,
            date: record.date,
            captured_at: record.capturedAt,
            buy: record.buy,
            sell: record.sell,
            quoteAvailable: true,
        };
        const enrichedEntity = enrichEntity(
            selectedEntity,
            official.official_rate
        );

        return {
            ...enrichedEntity,
            dailyChanges: {
                buy: findDailyChange(
                    record.buy,
                    date,
                    dashboardData.historyByEntity[currentEntity.id],
                    "buy"
                ),
                sell: findDailyChange(
                    record.sell,
                    date,
                    dashboardData.historyByEntity[currentEntity.id],
                    "sell"
                ),
            },
        };
    });

    return {
        ...dashboardData,
        official,
        entities,
        selectedDate: date,
        isHistorical: date !== dashboardData.official.date,
    };
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
    selectDashboardDate,
    sortEntities,
    loadEntityHistory,
    loadEntityChartData,
});
