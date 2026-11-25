
/* =========================================================
   1. APPLICATION STATE
   ========================================================= */

const state = {
    data: null,
    operation: "buy",
    display: "money",
    isLoading: false
};

let activeChartPeriod = "all";
let activeChartData = [];

let chartInstances = {
    rates: null,
    money: null,
    percentage: null,
};

let chartRequestId = 0;


/* =========================================================
   2. DOM ELEMENTS
   ========================================================= */

const elements = {
    officialRate: document.getElementById("official-rate"),
    officialDate: document.getElementById("official-date"),
    updatedAt: document.getElementById("updated-at"),

    entityList: document.getElementById("entity-list"),

    operationButtons: document.querySelectorAll(
        "[data-operation]"
    ),

    displayButtons: document.querySelectorAll(
        "[data-display]"
    ),

    modal: document.getElementById("entity-modal"),
    modalClose: document.getElementById("modal-close"),
    modalCompare: document.getElementById("modal-compare"),

    modalChartStatus: document.getElementById("modal-chart-status"),

    ratesChart: document.getElementById("rates-chart"),
    moneyChart: document.getElementById("money-chart"),
    percentageChart: document.getElementById("percentage-chart"),

    chartPeriodButtons: document.querySelectorAll("[data-period]")
};


/* =========================================================
   3. FORMATTERS
   ========================================================= */

const numberFormatter = new Intl.NumberFormat("es-BO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
});


function formatRate(value) {
    return numberFormatter.format(value);
}


function formatDifference(value, type) {
    const sign = value > 0 ? "+" : "";

    if (type === "money") {
        return `${sign}${formatRate(value)} Bs.`;
    }

    return `${sign}${formatRate(value)} %`;
}


function formatDate(value) {
    if (!value) {
        return "--";
    }

    const date = new Date(`${value}T12:00:00`);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat("es-BO", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        timeZone: "America/La_Paz"
    }).format(date);
}


function formatDateTime(value) {
    if (!value) {
        return "--";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "--";
    }

    return new Intl.DateTimeFormat("es-BO", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "America/La_Paz"
    }).format(date);
}


/* =========================================================
   4. DIFFERENCE PRESENTATION
   ========================================================= */

function getDifference(entity, rateType) {
    return entity.differences[rateType];
}


function getDifferenceClass(difference, rateType) {
    const isRelevantRate =
        (state.operation === "buy" && rateType === "sell") ||
        (state.operation === "sell" && rateType === "buy");

    if (!isRelevantRate || difference.money === 0) {
        return "difference--neutral";
    }

    const isFavorable =
        state.operation === "buy"
            ? difference.money < 0
            : difference.money > 0;

    return isFavorable
        ? "difference--favorable"
        : "difference--unfavorable";
}


function renderDifference(entity, rateType) {
    const difference = getDifference(entity, rateType);

    const value = state.display === "money"
        ? difference.money
        : difference.percentage;

    const differenceClass = getDifferenceClass(
        difference,
        rateType
    );

    return `
        <span class="entity-rate__difference ${differenceClass}">
            ${formatDifference(value, state.display)}
        </span>
    `;
}


/* =========================================================
   5. OFFICIAL RATE
   ========================================================= */

function renderOfficialRate() {
    const official = state.data.official;

    elements.officialRate.textContent = formatRate(
        official.official_rate
    );

    elements.officialDate.textContent = formatDate(
        official.date
    );

    elements.officialDate.dateTime = official.date;

    elements.updatedAt.textContent = formatDateTime(
        state.data.updatedAt
    );

    if (state.data.updatedAt) {
        elements.updatedAt.dateTime = state.data.updatedAt;
    }
}


/* =========================================================
   6. ENTITY CARD
   ========================================================= */

function renderEntity(entity, index) {
    const isBestRate = index === 0;

    const relevantRate = state.operation === "buy"
        ? "sell"
        : "buy";

    const relevantRateClass = relevantRate === "buy"
        ? "entity-rate--buy"
        : "entity-rate--sell";

    return `
        <article
            class="entity-card"
            data-entity-id="${escapeHTML(entity.id)}"
            tabindex="0"
            role="button"
            aria-label="Ver detalles de ${escapeHTML(entity.name)}"
        >

            <div class="entity-card__identity">

                <div class="entity-card__name-row">
                    <span class="entity-card__rank">
                        ${index + 1}
                    </span>

                    <h3 class="entity-card__name">
                        ${escapeHTML(entity.name)}
                    </h3>
                </div>

                <time
                    class="entity-card__date"
                    datetime="${escapeHTML(entity.date)}"
                >
                    Cotización: ${formatDate(entity.date)}
                </time>

                ${isBestRate ? `
                    <span class="entity-card__best">
                        Mejor opción
                    </span>
                ` : ""}

            </div>

            <div class="entity-card__rates">

                <div class="entity-rate ${
                    relevantRate === "buy" ? relevantRateClass : ""
                }">

                    <span class="entity-rate__value">
                        ${formatRate(entity.buy)}
                    </span>

                    ${renderDifference(entity, "buy")}

                </div>

                <div class="entity-rate ${
                    relevantRate === "sell" ? relevantRateClass : ""
                }">

                    <span class="entity-rate__value">
                        ${formatRate(entity.sell)}
                    </span>

                    ${renderDifference(entity, "sell")}

                </div>

            </div>

        </article>
    `;
}


/* =========================================================
   7. HTML ESCAPING
   ========================================================= */

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };

        return entities[character];
    });
}


/* =========================================================
   8. ENTITY LIST
   ========================================================= */

function renderEntityList() {
    const sortedEntities = DollarData.sortEntities(
        state.data.entities,
        state.operation
    );

    if (sortedEntities.length === 0) {
        elements.entityList.innerHTML = `
            <div class="entity-list__loading">
                No hay cotizaciones disponibles.
            </div>
        `;

        return;
    }

    elements.entityList.innerHTML = sortedEntities
        .map((entity, index) => renderEntity(entity, index))
        .join("");
}


/* =========================================================
   8.1. ENTITY DETAIL MODAL
   ========================================================= */

let activeModalEntity = null;
let previousFocusedElement = null;


function setModalDifference(elementId, value, type) {
    const element = document.getElementById(elementId);

    element.textContent = formatDifference(value, type);

    element.classList.remove(
        "difference--favorable",
        "difference--unfavorable",
        "difference--neutral"
    );

    if (value > 0) {
        element.classList.add("difference--unfavorable");
    } else if (value < 0) {
        element.classList.add("difference--favorable");
    } else {
        element.classList.add("difference--neutral");
    }
}


function renderModalDetails(entity) {
    const official = state.data.official;

    document.getElementById("modal-entity-name").textContent =
        entity.name;

    const entityDate = document.getElementById("modal-entity-date");

    entityDate.textContent = `Cotización: ${formatDate(entity.date)}`;
    entityDate.dateTime = entity.date;

    document.getElementById("modal-buy").textContent =
        `${formatRate(entity.buy)} Bs.`;

    document.getElementById("modal-sell").textContent =
        `${formatRate(entity.sell)} Bs.`;

    document.getElementById("modal-official-rate").textContent =
        `${formatRate(official.official_rate)} Bs.`;

    document.getElementById("modal-official-date").textContent =
        `Fecha: ${formatDate(official.date)}`;

    setModalDifference(
        "modal-buy-money",
        entity.differences.buy.money,
        "money"
    );

    setModalDifference(
        "modal-buy-percentage",
        entity.differences.buy.percentage,
        "percentage"
    );

    setModalDifference(
        "modal-sell-money",
        entity.differences.sell.money,
        "money"
    );

    setModalDifference(
        "modal-sell-percentage",
        entity.differences.sell.percentage,
        "percentage"
    );
}


function openEntityModal(entity) {
    if (!entity) {
        return;
    }

    activeModalEntity = entity;
    previousFocusedElement = document.activeElement;

    renderModalDetails(entity);

    elements.modal.hidden = false;

    elements.modal.setAttribute("aria-hidden", "false");

    document.body.style.overflow = "hidden";

    elements.modalClose.focus();

    loadModalChartData(entity.id);
}


function closeEntityModal() {
    if (elements.modal.hidden) {
        return;
    }

    elements.modal.hidden = true;

    elements.modal.setAttribute("aria-hidden", "true");

    document.body.style.overflow = "";

    activeModalEntity = null;

    if (previousFocusedElement) {
        previousFocusedElement.focus();
    }

    chartRequestId++;
    activeChartData = [];

    destroyCharts();
}


function compareModalEntity() {
    if (!activeModalEntity) {
        return;
    }

    const entityId = encodeURIComponent(activeModalEntity.id);

    window.location.href =
        `./pages/compare.html?entity=${entityId}`;
}


function handleModalKeyboard(event) {
    if (elements.modal.hidden) {
        return;
    }

    if (event.key === "Escape") {
        closeEntityModal();
        return;
    }

    if (event.key !== "Tab") {
        return;
    }

    const focusableElements = elements.modal.querySelectorAll(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );

    const focusable = [...focusableElements];

    if (focusable.length === 0) {
        event.preventDefault();
        return;
    }

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (
        event.shiftKey &&
        document.activeElement === first
    ) {
        event.preventDefault();
        last.focus();

    } else if (
        !event.shiftKey &&
        document.activeElement === last
    ) {
        event.preventDefault();
        first.focus();
    }
}


/* =========================================================
   9. CONTROL BUTTONS
   ========================================================= */

function updateButtonStates(buttons, attribute, selectedValue) {
    buttons.forEach(button => {
        const isActive = button.dataset[attribute] === selectedValue;

        button.classList.toggle("is-active", isActive);

        button.setAttribute(
            "aria-pressed",
            String(isActive)
        );
    });
}


function handleOperationChange(operation) {
    if (!["buy", "sell"].includes(operation)) {
        return;
    }

    state.operation = operation;

    updateButtonStates(
        elements.operationButtons,
        "operation",
        state.operation
    );

    if (state.data) {
        renderEntityList();
    }
}


function handleDisplayChange(display) {
    if (!["money", "percentage"].includes(display)) {
        return;
    }

    state.display = display;

    updateButtonStates(
        elements.displayButtons,
        "display",
        state.display
    );

    if (state.data) {
        renderEntityList();
    }
}


/* =========================================================
   10. LOADING AND ERROR STATES
   ========================================================= */

function renderLoadingState() {
    elements.entityList.innerHTML = `
        <div class="entity-list__loading">
            Cargando cotizaciones...
        </div>
    `;
}


function renderErrorState(error) {
    console.error("Dashboard loading error:", error);

    elements.entityList.innerHTML = `
        <div class="entity-list__loading">
            <div class="entity-list__error">

                <p>
                    No fue posible cargar las cotizaciones.
                </p>

                <button
                    type="button"
                    class="entity-list__retry"
                    data-action="retry"
                >
                    Intentar nuevamente
                </button>

            </div>
        </div>
    `;
}


/* =========================================================
   11. DASHBOARD INITIALIZATION
   ========================================================= */

async function initializeDashboard() {
    if (state.isLoading) {
        return;
    }

    state.isLoading = true;

    renderLoadingState();

    try {
        state.data = await DollarData.loadDashboardData();

        renderOfficialRate();
        renderEntityList();

    } catch (error) {
        state.data = null;

        renderErrorState(error);

    } finally {
        state.isLoading = false;
    }
}


/* =========================================================
   12. EVENT LISTENERS
   ========================================================= */

function initializeEventListeners() {

    elements.operationButtons.forEach(button => {
        button.addEventListener("click", () => {
            handleOperationChange(
                button.dataset.operation
            );
        });
    });

    elements.displayButtons.forEach(button => {
        button.addEventListener("click", () => {
            handleDisplayChange(
                button.dataset.display
            );
        });
    });

    elements.entityList.addEventListener("click", event => {
        const retryButton = event.target.closest(
            '[data-action="retry"]'
        );

        if (retryButton) {
            initializeDashboard();
        }
    });

    elements.entityList.addEventListener("click", event => {
        const card = event.target.closest("[data-entity-id]");

        if (!card || !state.data) {
            return;
        }

        const entity = state.data.entities.find(
            item => item.id === card.dataset.entityId
        );

        openEntityModal(entity);
    });

    elements.entityList.addEventListener("keydown", event => {
        if (
            event.key !== "Enter" &&
            event.key !== " "
        ) {
            return;
        }

        const card = event.target.closest("[data-entity-id]");

        if (!card || !state.data) {
            return;
        }

        event.preventDefault();

        const entity = state.data.entities.find(
            item => item.id === card.dataset.entityId
        );

        openEntityModal(entity);
    });

    elements.modalClose.addEventListener(
        "click",
        closeEntityModal
    );

    elements.modal.addEventListener("click", event => {
        if (event.target.matches("[data-modal-close]")) {
            closeEntityModal();
        }
    });

    elements.modalCompare.addEventListener(
        "click",
        compareModalEntity
    );

    document.addEventListener(
        "keydown",
        handleModalKeyboard
    );

    initializeChartPeriodButtons();
}


/* =========================================================
   12.1. CHART PERIOD FILTERING
   ========================================================= */

function filterChartData(records, period) {
    if (period === "all" || records.length === 0) {
        return records;
    }

    const daysByPeriod = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "6mo": 183,
        "1y": 365,
    };

    const days = daysByPeriod[period];

    if (!days) {
        return records;
    }

    const latestDate = new Date(
        `${records[records.length - 1].date}T12:00:00`
    );

    if (Number.isNaN(latestDate.getTime())) {
        return records;
    }

    const cutoffDate = new Date(latestDate);

    // Inclusive range: 7 calendar days means today + 6 previous days.
    cutoffDate.setDate(cutoffDate.getDate() - (days - 1));

    const cutoff = cutoffDate.toISOString().slice(0, 10);

    return records.filter(record => record.date >= cutoff);
}


/* =========================================================
   12.2. CHART INSTANCE MANAGEMENT
   ========================================================= */

function destroyCharts() {
    Object.values(chartInstances).forEach(chart => {
        if (chart) {
            chart.destroy();
        }
    });

    chartInstances = {
        rates: null,
        money: null,
        percentage: null,
    };
}


/* =========================================================
   12.3. CHART FORMATTERS AND OPTIONS
   ========================================================= */

function formatChartDate(value) {
    const date = new Date(`${value}T12:00:00`);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat("es-BO", {
        day: "2-digit",
        month: "short",
        timeZone: "America/La_Paz",
    }).format(date);
}


function createChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,

        interaction: {
            mode: "index",
            intersect: false,
        },

        plugins: {
            legend: {
                position: "bottom",

                labels: {
                    color: "#a0aec0",
                    usePointStyle: true,
                    padding: 18,
                },
            },
        },

        scales: {
            x: {
                ticks: {
                    color: "#718096",
                    maxRotation: 0,
                    autoSkip: true,
                },

                grid: {
                    color: "rgba(113, 128, 150, 0.12)",
                },
            },

            y: {
                ticks: {
                    color: "#718096",
                },

                grid: {
                    color: "rgba(113, 128, 150, 0.12)",
                },
            },
        },
    };
}


function createLineDataset(label, data, color) {
    return {
        label,
        data,

        borderColor: color,
        backgroundColor: color,

        borderWidth: 2,

        pointRadius: 3,
        pointHoverRadius: 6,

        tension: 0.2,
        spanGaps: false,
    };
}


function hasNumericValue(value) {
    return (
        value !== null &&
        value !== undefined &&
        Number.isFinite(Number(value))
    );
}


/* =========================================================
   12.4. CHART PERIOD BUTTON STATES
   ========================================================= */

function updateChartPeriodButtons(selectedPeriod) {
    elements.chartPeriodButtons.forEach(button => {
        const isActive =
            button.dataset.period === selectedPeriod;

        button.classList.toggle("is-active", isActive);

        button.setAttribute(
            "aria-pressed",
            String(isActive)
        );
    });
}


/* =========================================================
   12.5. HISTORICAL CHART RENDERING
   ========================================================= */

function renderHistoricalCharts() {
    const status = elements.modalChartStatus;

    const filteredData = filterChartData(
        activeChartData,
        activeChartPeriod
    );

    destroyCharts();

    if (filteredData.length === 0) {
        status.textContent =
            "No hay registros históricos disponibles para este período.";

        return;
    }

    const hasRateData = filteredData.some(record =>
        hasNumericValue(record.officialRate) ||
        hasNumericValue(record.buy) ||
        hasNumericValue(record.sell)
    );

    if (!hasRateData) {
        status.textContent = "No hay cotizaciones disponibles.";
        return;
    }

    if (typeof Chart === "undefined") {
        status.textContent =
            "No se pudo cargar la biblioteca de gráficos.";

        console.error("Chart.js is not available.");

        return;
    }

    const labels = filteredData.map(record =>
        formatChartDate(record.date)
    );

    status.textContent =
        `${filteredData.length} registros disponibles en este período.`;

    chartInstances.rates = new Chart(
        elements.ratesChart,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    createLineDataset(
                        "BCB oficial",
                        filteredData.map(record =>
                            record.officialRate ?? null
                        ),
                        "#8797f5"
                    ),

                    createLineDataset(
                        "Compra",
                        filteredData.map(record =>
                            record.buy ?? null
                        ),
                        "#42d6a0"
                    ),

                    createLineDataset(
                        "Venta",
                        filteredData.map(record =>
                            record.sell ?? null
                        ),
                        "#f17d83"
                    ),
                ],
            },

            options: createChartOptions(),
        }
    );

    chartInstances.money = new Chart(
        elements.moneyChart,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    createLineDataset(
                        "Compra",
                        filteredData.map(record =>
                            record.buyDifference?.money ?? null
                        ),
                        "#42d6a0"
                    ),

                    createLineDataset(
                        "Venta",
                        filteredData.map(record =>
                            record.sellDifference?.money ?? null
                        ),
                        "#f17d83"
                    ),
                ],
            },

            options: createChartOptions(),
        }
    );

    chartInstances.percentage = new Chart(
        elements.percentageChart,
        {
            type: "line",

            data: {
                labels,

                datasets: [
                    createLineDataset(
                        "Compra",
                        filteredData.map(record =>
                            record.buyDifference?.percentage ?? null
                        ),
                        "#42d6a0"
                    ),

                    createLineDataset(
                        "Venta",
                        filteredData.map(record =>
                            record.sellDifference?.percentage ?? null
                        ),
                        "#f17d83"
                    ),
                ],
            },

            options: createChartOptions(),
        }
    );
}


/* =========================================================
   12.6. HISTORICAL DATA LOADING
   ========================================================= */

async function loadModalChartData(entityId) {
    const requestId = ++chartRequestId;

    elements.modalChartStatus.textContent =
        "Cargando historial...";

    activeChartData = [];

    destroyCharts();

    try {
        const records = await DollarData.loadEntityChartData(entityId);

        // Ignore responses from an entity that is no longer selected.
        if (requestId !== chartRequestId) {
            return;
        }

        activeChartData = records;

        activeChartPeriod = "all";

        updateChartPeriodButtons("all");

        renderHistoricalCharts();

    } catch (error) {
        if (requestId !== chartRequestId) {
            return;
        }

        elements.modalChartStatus.textContent =
            "No se pudo cargar el historial.";

        console.error("Historical charts error:", error);
    }
}


/* =========================================================
   12.7. CHART PERIOD EVENT LISTENERS
   ========================================================= */

function initializeChartPeriodButtons() {
    elements.chartPeriodButtons.forEach(button => {
        button.addEventListener("click", () => {
            const selectedPeriod = button.dataset.period;

            activeChartPeriod = selectedPeriod;

            updateChartPeriodButtons(selectedPeriod);

            renderHistoricalCharts();
        });
    });

    updateChartPeriodButtons(activeChartPeriod);
}


/* =========================================================
   13. APPLICATION START
   ========================================================= */

function initializeApp() {
    initializeEventListeners();
    initializeDashboard();
}


document.addEventListener(
    "DOMContentLoaded",
    initializeApp,
    { once: true }
);
