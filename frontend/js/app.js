
/* =========================================================
   1. APPLICATION STATE
   ========================================================= */

const state = {
    data: null,
    currentData: null,
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
let availableQuoteDates = new Set();
let mobileCalendarMonth = null;


/* =========================================================
   2. DOM ELEMENTS
   ========================================================= */

const elements = {
    officialRate: document.getElementById("official-rate"),
    updatedAt: document.getElementById("updated-at"),
    quoteDate: document.getElementById("quote-date"),
    quoteDateStatus: document.getElementById("quote-date-status"),
    mobileCalendar: document.getElementById("mobile-date-picker"),
    mobileCalendarTrigger: document.getElementById("mobile-date-trigger"),
    mobileCalendarSelected: document.getElementById("mobile-date-selected"),
    mobileCalendarPanel: document.getElementById("mobile-date-panel"),
    mobileCalendarMonth: document.getElementById("mobile-date-month"),
    mobileCalendarDays: document.getElementById("mobile-date-days"),
    mobileCalendarPrevious: document.getElementById("mobile-date-previous"),
    mobileCalendarNext: document.getElementById("mobile-date-next"),

    entityList: document.getElementById("entity-list"),
    entityItems: document.getElementById("entity-list-items"),

    operationButtons: document.querySelectorAll(
        '[data-mode-toggle="operation"]'
    ),

    displayButtons: document.querySelectorAll(
        '[data-mode-toggle="display"]'
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


function dailyChangeTone(change, reverseDirection = false) {
    if (!change || change.money === 0) {
        return "neutral";
    }

    if (reverseDirection) {
        return change.money < 0 ? "up" : "down";
    }

    return change.money < 0 ? "down" : "up";
}


function describeDailyChange(change, display = "both") {
    if (!change) {
        return "No hay una cotización anterior disponible para comparar.";
    }

    if (change.money === 0) {
        return "La cotización no varió respecto a la cotización anterior.";
    }

    const direction = change.money < 0 ? "Bajó" : "Subió";
    const value = display === "money"
        ? `${formatRate(Math.abs(change.money))} bolivianos`
        : display === "percentage"
            ? `${formatRate(Math.abs(change.percentage))} por ciento`
            : `${formatRate(Math.abs(change.money))} bolivianos ` +
                `(${formatRate(Math.abs(change.percentage))} por ciento)`;

    return `${direction} ${value} respecto a la cotización anterior.`;
}


function formatDailyChange(change, display = "both") {
    if (!change) {
        return "Sin dato previo";
    }

    const arrow = change.money < 0 ? "↓" : change.money > 0 ? "↑" : "→";
    const moneySign = change.money > 0 ? "+" : change.money < 0 ? "−" : "";
    const percentageSign = change.percentage > 0
        ? "+"
        : change.percentage < 0
            ? "−"
            : "";

    const moneyValue = `${moneySign}${formatRate(Math.abs(change.money))} Bs.`;
    const percentageValue =
        `${percentageSign}${formatRate(Math.abs(change.percentage))}%`;

    if (display === "money") {
        return `${arrow} ${moneyValue}`;
    }

    if (display === "percentage") {
        return `${arrow} ${percentageValue}`;
    }

    return `${arrow} ${moneyValue} (${percentageValue})`;
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


function parseISODate(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day, 12);
}


function toISODate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


function formatAccessibleDate(value) {
    return new Intl.DateTimeFormat("es-BO", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "America/La_Paz",
    }).format(parseISODate(value));
}


function calendarMonthIndex(date) {
    return date.getFullYear() * 12 + date.getMonth();
}


function renderMobileCalendar() {
    if (!state.currentData || !mobileCalendarMonth) {
        return;
    }

    const availableDates = [...availableQuoteDates].sort();
    if (availableDates.length === 0) {
        return;
    }

    const firstAvailableDate = parseISODate(availableDates[0]);
    const lastAvailableDate = parseISODate(availableDates[availableDates.length - 1]);
    const year = mobileCalendarMonth.getFullYear();
    const month = mobileCalendarMonth.getMonth();
    const firstOfMonth = new Date(year, month, 1, 12);
    const daysInMonth = new Date(year, month + 1, 0, 12).getDate();
    const mondayFirstOffset = (firstOfMonth.getDay() + 6) % 7;
    const selectedDate = state.data.selectedDate;
    const monthLabel = new Intl.DateTimeFormat("es-BO", {
        month: "long",
        year: "numeric",
        timeZone: "America/La_Paz",
    }).format(firstOfMonth);

    elements.mobileCalendarMonth.textContent =
        monthLabel.charAt(0).toLocaleUpperCase("es-BO") + monthLabel.slice(1);
    elements.mobileCalendarPrevious.disabled =
        calendarMonthIndex(firstOfMonth) <= calendarMonthIndex(firstAvailableDate);
    elements.mobileCalendarNext.disabled =
        calendarMonthIndex(firstOfMonth) >= calendarMonthIndex(lastAvailableDate);
    elements.mobileCalendarDays.replaceChildren();

    for (let offset = 0; offset < mondayFirstOffset; offset += 1) {
        const emptyDay = document.createElement("li");
        emptyDay.setAttribute("aria-hidden", "true");
        elements.mobileCalendarDays.append(emptyDay);
    }

    const today = toISODate(new Date());
    for (let day = 1; day <= daysInMonth; day += 1) {
        const date = new Date(year, month, day, 12);
        const dateValue = toISODate(date);
        const isAvailable = availableQuoteDates.has(dateValue);
        const item = document.createElement("li");
        const dayButton = document.createElement("button");

        dayButton.type = "button";
        dayButton.className = "mobile-date-picker__day";
        dayButton.textContent = String(day);
        dayButton.disabled = !isAvailable;
        dayButton.dataset.date = dateValue;
        dayButton.setAttribute("aria-label", isAvailable
            ? formatAccessibleDate(dateValue)
            : `${formatAccessibleDate(dateValue)}, sin cotización disponible`);
        dayButton.setAttribute("aria-pressed", String(dateValue === selectedDate));

        if (dateValue === selectedDate) {
            dayButton.classList.add("is-selected");
        }
        if (dateValue === today) {
            dayButton.setAttribute("aria-current", "date");
        }

        dayButton.addEventListener("click", () => selectMobileCalendarDate(dateValue));
        item.append(dayButton);
        elements.mobileCalendarDays.append(item);
    }
}


function updateMobileCalendarSelection(date) {
    if (!date || !elements.mobileCalendarSelected) {
        return;
    }

    elements.mobileCalendarSelected.textContent = formatDate(date);
    elements.mobileCalendarTrigger.setAttribute(
        "aria-label",
        `Fecha seleccionada: ${formatAccessibleDate(date)}. Abrir calendario.`
    );
    if (elements.mobileCalendarPanel && !elements.mobileCalendarPanel.hidden) {
        mobileCalendarMonth = parseISODate(date);
        renderMobileCalendar();
    }
}


function openMobileCalendar() {
    if (!state.currentData) {
        return;
    }

    mobileCalendarMonth = parseISODate(state.data.selectedDate);
    renderMobileCalendar();
    elements.mobileCalendarPanel.hidden = false;
    elements.mobileCalendarTrigger.setAttribute("aria-expanded", "true");

    const selectedDay = elements.mobileCalendarDays.querySelector(
        ".mobile-date-picker__day.is-selected:not(:disabled)"
    );
    const firstAvailableDay = elements.mobileCalendarDays.querySelector(
        ".mobile-date-picker__day:not(:disabled)"
    );
    (selectedDay ?? firstAvailableDay ?? elements.mobileCalendarPrevious).focus();
}


function closeMobileCalendar({ restoreFocus = false } = {}) {
    elements.mobileCalendarPanel.hidden = true;
    elements.mobileCalendarTrigger.setAttribute("aria-expanded", "false");

    if (restoreFocus) {
        elements.mobileCalendarTrigger.focus();
    }
}


function selectMobileCalendarDate(date) {
    if (!availableQuoteDates.has(date)) {
        return;
    }

    elements.quoteDate.value = date;
    applyQuoteDate(date);
    closeMobileCalendar({ restoreFocus: true });
}


function moveMobileCalendarMonth(offset) {
    if (!mobileCalendarMonth) {
        return;
    }

    const nextMonth = new Date(
        mobileCalendarMonth.getFullYear(),
        mobileCalendarMonth.getMonth() + offset,
        1,
        12
    );
    const dates = [...availableQuoteDates].sort();
    const firstMonth = parseISODate(dates[0]);
    const lastMonth = parseISODate(dates[dates.length - 1]);

    if (
        calendarMonthIndex(nextMonth) < calendarMonthIndex(firstMonth) ||
        calendarMonthIndex(nextMonth) > calendarMonthIndex(lastMonth)
    ) {
        return;
    }

    mobileCalendarMonth = nextMonth;
    renderMobileCalendar();
}


function handleMobileCalendarKeydown(event) {
    const dayButton = event.target.closest(".mobile-date-picker__day");
    if (!dayButton || dayButton.disabled) {
        return;
    }

    const offsets = {
        ArrowLeft: -1,
        ArrowRight: 1,
        ArrowUp: -7,
        ArrowDown: 7,
    };

    if (event.key === "PageUp" || event.key === "PageDown") {
        event.preventDefault();
        moveMobileCalendarMonth(event.key === "PageUp" ? -1 : 1);
        const focusTarget = elements.mobileCalendarDays.querySelector(
            ".mobile-date-picker__day.is-selected:not(:disabled), .mobile-date-picker__day:not(:disabled)"
        );
        focusTarget?.focus();
        return;
    }

    const offset = offsets[event.key];
    if (offset === undefined) {
        return;
    }

    event.preventDefault();
    const candidate = parseISODate(dayButton.dataset.date);
    candidate.setDate(candidate.getDate() + offset);
    const direction = Math.sign(offset);
    const availableDates = [...availableQuoteDates].sort();
    const firstAvailableDate = availableDates[0];
    const lastAvailableDate = availableDates[availableDates.length - 1];

    for (let attempt = 0; attempt < 3700; attempt += 1) {
        const candidateValue = toISODate(candidate);
        if (candidateValue < firstAvailableDate || candidateValue > lastAvailableDate) {
            return;
        }
        if (availableQuoteDates.has(candidateValue)) {
            mobileCalendarMonth = parseISODate(candidateValue);
            renderMobileCalendar();
            elements.mobileCalendarDays
                .querySelector(`[data-date="${candidateValue}"]`)
                ?.focus();
            return;
        }

        candidate.setDate(candidate.getDate() + direction);
    }
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


function getDifferenceClass() {
    return "difference--neutral";
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

    setDailyChange(
        document.getElementById("official-daily-change"),
        official.dailyChange,
        "Variación diaria de la cotización oficial del BCB"
    );

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
    if (entity.quoteAvailable === false) {
        return `
            <article class="entity-card entity-card--unavailable" aria-label="Sin cotización guardada para ${escapeHTML(entity.name)}">
                <div class="entity-card__identity">
                    <div class="entity-card__name-row">
                        <span class="entity-card__rank">${index + 1}</span>
                        <div class="entity-card__name-details">
                            <h3 class="entity-card__name">${escapeHTML(entity.name)}</h3>
                            <span class="entity-card__unavailable">Sin cotización para esta fecha</span>
                        </div>
                    </div>
                </div>
                <div class="entity-card__rates" aria-hidden="true">
                    <div class="entity-rate"><span class="entity-rate__label">Compra</span><span class="entity-rate__value">--</span></div>
                    <div class="entity-rate"><span class="entity-rate__label">Venta</span><span class="entity-rate__value">--</span></div>
                </div>
            </article>
        `;
    }

    const isBestRate = entity.quoteAvailable !== false && index === 0;

    const relevantRate = state.operation === "buy"
        ? "sell"
        : "buy";

    const relevantRateClass = relevantRate === "buy"
        ? "entity-rate--buy"
        : "entity-rate--sell";

    return `
        <article
            class="entity-card${isBestRate ? " entity-card--best" : ""}"
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

                    <div class="entity-card__name-details">
                        <h3 class="entity-card__name">
                            ${escapeHTML(entity.name)}
                        </h3>
                    </div>
                </div>

            </div>

            <div class="entity-card__rates">

                <div class="entity-rate ${
                    relevantRate === "buy" ? relevantRateClass : ""
                }">

                    <span class="entity-rate__label">Compra</span>

                    <span class="entity-rate__value">
                        ${formatRate(entity.buy)}
                    </span>

                    ${renderDifference(entity, "buy")}

                </div>

                <div class="entity-rate ${
                    relevantRate === "sell" ? relevantRateClass : ""
                }">

                    <span class="entity-rate__label">Venta</span>

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
        elements.entityItems.innerHTML = `
            <div class="entity-list__loading">
                No hay cotizaciones disponibles.
            </div>
        `;
        elements.entityList.setAttribute("aria-busy", "false");

        return;
    }

    elements.entityItems.innerHTML = sortedEntities
        .map((entity, index) => renderEntity(entity, index))
        .join("");
    elements.entityList.setAttribute("aria-busy", "false");
}


/* =========================================================
   8.1. ENTITY DETAIL MODAL
   ========================================================= */

let activeModalEntity = null;
let previousFocusedElement = null;


function setModalDifference(elementId, value, type) {
    const element = document.getElementById(elementId);

    element.textContent = formatDifference(value, type);
    element.classList.remove("difference--favorable", "difference--unfavorable");
    element.classList.add("difference--neutral");
    element.hidden = type !== state.display;
}


function setDailyChange(
    element,
    change,
    accessibleLabel,
    { reverseDirection = false, display = "both" } = {}
) {
    const tone = dailyChangeTone(change, reverseDirection);
    const accessibleText = `${accessibleLabel}. ${describeDailyChange(change, display)}`;

    element.className = `${element.className
        .split(" ")
        .filter(className => !className.startsWith("daily-change--"))
        .join(" ")} daily-change--${tone}`;
    element.textContent = formatDailyChange(change, display);
    element.setAttribute("role", "img");
    element.setAttribute("aria-label", accessibleText);
}


function renderModalDetails(entity) {
    const official = state.data.official;

    document.getElementById("modal-entity-name").textContent =
        entity.name;

    const entityDate = document.getElementById("modal-entity-date");

    entityDate.textContent = formatDate(entity.date);
    entityDate.dateTime = entity.date;
    entityDate.setAttribute(
        "aria-label",
        `Fecha de cotización de ${entity.name}: ${formatDate(entity.date)}`
    );

    document.getElementById("modal-buy").textContent =
        `${formatRate(entity.buy)} Bs.`;

    document.getElementById("modal-sell").textContent =
        `${formatRate(entity.sell)} Bs.`;

    document.getElementById("modal-official-rate").textContent =
        `${formatRate(official.official_rate)} Bs.`;

    setDailyChange(
        document.getElementById("modal-buy-daily-change"),
        entity.dailyChanges?.buy,
        `Variación diaria de compra de ${entity.name}`,
        { reverseDirection: true, display: state.display }
    );

    setDailyChange(
        document.getElementById("modal-sell-daily-change"),
        entity.dailyChanges?.sell,
        `Variación diaria de venta de ${entity.name}`,
        { display: state.display }
    );

    setDailyChange(
        document.getElementById("modal-official-daily-change"),
        official.dailyChange,
        "Variación diaria de la cotización oficial del BCB",
        { display: state.display }
    );

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

function updateModeButtons() {
    const operationLabel = state.operation === "buy"
        ? "Comprar USD"
        : "Vender USD";
    const displayLabel = state.display === "money" ? "Bs." : "%";
    const displayDescription = state.display === "money"
        ? "bolivianos"
        : "porcentaje";

    elements.operationButtons.forEach(button => {
        button.textContent = operationLabel;
        button.setAttribute(
            "aria-label",
            `Operación actual: ${operationLabel}. Activar para cambiar.`
        );
    });

    elements.displayButtons.forEach(button => {
        button.textContent = displayLabel;
        button.setAttribute(
            "aria-label",
            `Formato actual: ${displayDescription}. Activar para cambiar.`
        );
    });
}


function handleOperationChange(operation) {
    if (!["buy", "sell"].includes(operation)) {
        return;
    }

    state.operation = operation;
    updateModeButtons();

    if (state.data) {
        renderEntityList();
    }
}


function handleDisplayChange(display) {
    if (!["money", "percentage"].includes(display)) {
        return;
    }

    state.display = display;
    updateModeButtons();

    if (state.data) {
        renderEntityList();

        if (!elements.modal.hidden && activeModalEntity) {
            renderModalDetails(activeModalEntity);
        }
    }
}


function applyQuoteDate(selectedDate) {
    if (!state.currentData) {
        return;
    }

    if (!selectedDate) {
        elements.quoteDate.value = state.data.selectedDate;
        updateMobileCalendarSelection(state.data.selectedDate);
        return;
    }

    const selectedData = availableQuoteDates.has(selectedDate)
        ? selectedDate === state.currentData.official.date
            ? state.currentData
            : DollarData.selectDashboardDate(state.currentData, selectedDate)
        : null;

    if (!selectedData) {
        elements.quoteDateStatus.textContent =
            `No hay una cotización oficial guardada para ${formatDate(selectedDate)}.`;
        elements.quoteDate.value = state.data.selectedDate ?? state.currentData.official.date;
        updateMobileCalendarSelection(elements.quoteDate.value);
        return;
    }

    elements.quoteDateStatus.textContent = "";
    elements.quoteDate.value = selectedDate;
    updateMobileCalendarSelection(selectedDate);
    state.data = selectedData;
    renderOfficialRate();
    renderEntityList();
}


function handleQuoteDateChange(event) {
    applyQuoteDate(event.currentTarget.value);
}


/* =========================================================
   10. LOADING AND ERROR STATES
   ========================================================= */

function renderLoadingState() {
    elements.entityList.setAttribute("aria-busy", "true");
    elements.entityItems.innerHTML = `
        <div class="entity-list__loading">
            Cargando cotizaciones...
        </div>
    `;
}


function renderErrorState(error) {
    console.error("Dashboard loading error:", error);
    elements.entityList.setAttribute("aria-busy", "false");

    elements.entityItems.innerHTML = `
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
        state.currentData = await DollarData.loadDashboardData();
        state.data = state.currentData;

        const availableDates = state.currentData.availableDates;
        availableQuoteDates = new Set(availableDates);
        elements.quoteDate.min = availableDates[0] ?? state.currentData.official.date;
        elements.quoteDate.max = state.currentData.official.date;
        elements.quoteDate.value = state.currentData.official.date;
        mobileCalendarMonth = parseISODate(state.currentData.official.date);
        updateMobileCalendarSelection(state.currentData.official.date);
        renderMobileCalendar();

        renderOfficialRate();
        renderEntityList();

    } catch (error) {
        state.data = null;
        state.currentData = null;

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
            handleOperationChange(state.operation === "buy" ? "sell" : "buy");
        });
    });

    elements.displayButtons.forEach(button => {
        button.addEventListener("click", () => {
            handleDisplayChange(
                state.display === "money" ? "percentage" : "money"
            );
        });
    });

    elements.quoteDate.addEventListener("change", handleQuoteDateChange);
    elements.mobileCalendarTrigger.addEventListener("click", () => {
        if (elements.mobileCalendarPanel.hidden) {
            openMobileCalendar();
        } else {
            closeMobileCalendar();
        }
    });
    elements.mobileCalendarPrevious.addEventListener("click", () => {
        moveMobileCalendarMonth(-1);
    });
    elements.mobileCalendarNext.addEventListener("click", () => {
        moveMobileCalendarMonth(1);
    });
    elements.mobileCalendarDays.addEventListener(
        "keydown",
        handleMobileCalendarKeydown
    );
    document.addEventListener("click", event => {
        if (
            !elements.mobileCalendarPanel.hidden &&
            !elements.mobileCalendar.contains(event.target)
        ) {
            closeMobileCalendar();
        }
    });
    document.addEventListener("keydown", event => {
        if (event.key === "Escape" && !elements.mobileCalendarPanel.hidden) {
            closeMobileCalendar({ restoreFocus: true });
        }
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
    updateModeButtons();
    initializeDashboard();
}


document.addEventListener(
    "DOMContentLoaded",
    initializeApp,
    { once: true }
);
