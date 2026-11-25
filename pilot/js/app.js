
const DATA_URL = "../frontend/data/current.json";

const elements = {
    connectionStatus: document.querySelector("#connection-status"),
    updatedAt: document.querySelector("#updated-at"),

    officialRate: document.querySelector("#official-rate"),
    officialDate: document.querySelector("#official-date"),

    bankCount: document.querySelector("#bank-count"),
    bankList: document.querySelector("#bank-list"),

    listDescription: document.querySelector("#list-description"),

    operationButtons: document.querySelectorAll(
        ".operation-button"
    ),
};

let quotes = [];
let officialRate = null;
let operation = "buy";


/* FORMATTING */

function formatRate(value) {
    return new Intl.NumberFormat("es-BO", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 4,
    }).format(Number(value));
}


function formatVariation(value) {
    const sign = value > 0 ? "+" : "";

    return `${sign}${new Intl.NumberFormat("es-BO", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    }).format(value)} %`;
}


function formatDate(value) {
    if (!value) return "--";

    const date = new Date(
        value.length === 10 ? `${value}T12:00:00` : value
    );

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat("es-BO", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    }).format(date);
}


function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    })[char]);
}


/* DATA EXTRACTION */

function extractQuotes(data) {
    if (Array.isArray(data)) {
        return data;
    }

    if (Array.isArray(data.quotes)) {
        return data.quotes;
    }

    if (Array.isArray(data.data)) {
        return data.data;
    }

    if (data.entities && typeof data.entities === "object") {
        return Object.values(data.entities);
    }

    return Object.entries(data)
        .filter(([key, value]) =>
            key !== "updated_at" &&
            value &&
            typeof value === "object" &&
            !Array.isArray(value) &&
            (value.id || value.type)
        )
        .map(([key, value]) => ({
            ...value,
            id: value.id ?? key,
        }));
}


/* VARIATION */

function calculateVariation(rate) {
    if (
        !Number.isFinite(Number(rate)) ||
        !Number.isFinite(Number(officialRate)) ||
        Number(officialRate) <= 0
    ) {
        return null;
    }

    return (
        (Number(rate) - Number(officialRate)) /
        Number(officialRate)
    ) * 100;
}


function renderVariation(rate) {
    const variation = calculateVariation(rate);

    if (variation === null) {
        return `
            <span class="rate-variation equal">--</span>
        `;
    }

    let variationClass = "equal";

    if (variation > 0) {
        variationClass = "above";
    } else if (variation < 0) {
        variationClass = "below";
    }

    return `
        <span class="rate-variation ${variationClass}">
            ${formatVariation(variation)}
        </span>
    `;
}


/* OFFICIAL QUOTE */

function renderOfficialQuote(quote) {
    if (!quote || !Number.isFinite(Number(quote.official_rate))) {
        throw new Error("No se encontró una cotización oficial válida del BCB.");
    }

    officialRate = Number(quote.official_rate);

    elements.officialRate.textContent = formatRate(officialRate);

    elements.officialDate.textContent =
        `Fecha de cotización: ${formatDate(quote.date)}`;
}


/* SORTING */

function getSortedBanks() {
    const banks = quotes
        .filter(quote => quote.type === "commercial_bank")
        .filter(quote =>
            Number.isFinite(Number(quote.buy)) &&
            Number.isFinite(Number(quote.sell)) &&
            Number(quote.buy) > 0 &&
            Number(quote.sell) > 0
        );

    const field = operation === "buy" ? "sell" : "buy";

    return banks.sort((a, b) => {
        const first = Number(a[field]);
        const second = Number(b[field]);

        return operation === "buy"
            ? first - second
            : second - first;
    });
}


/* BANK RENDERING */

function renderBanks() {
    const banks = getSortedBanks();

    elements.bankCount.textContent =
        `${banks.length} ${banks.length === 1 ? "banco" : "bancos"}`;

    elements.listDescription.textContent =
        operation === "buy"
            ? "Bancos ordenados por menor precio de venta."
            : "Bancos ordenados por mayor precio de compra.";

    if (!banks.length) {
        elements.bankList.innerHTML = `
            <div class="empty-state">
                No hay cotizaciones bancarias disponibles.
            </div>
        `;

        return;
    }

    elements.bankList.innerHTML = banks.map((bank, index) => {
        const selectedBuy = operation === "sell";
        const selectedSell = operation === "buy";

        return `
            <article class="bank-card">

                <div class="bank-identity">

                    <span class="bank-rank">
                        ${index + 1}
                    </span>

                    <div>
                        <div class="bank-name">
                            ${escapeHTML(bank.name)}
                        </div>

                        <div class="bank-date">
                            Cotización: ${escapeHTML(formatDate(bank.date))}
                        </div>
                    </div>

                </div>


                <div class="bank-rates">

                    <div class="rate-item ${selectedBuy ? "selected buy" : ""}">

                        <span class="rate-label">
                            COMPRA
                        </span>

                        <strong class="rate-value">
                            ${formatRate(bank.buy)}
                        </strong>

                        ${renderVariation(bank.buy)}

                    </div>


                    <div class="rate-item ${selectedSell ? "selected sell" : ""}">

                        <span class="rate-label">
                            VENTA
                        </span>

                        <strong class="rate-value">
                            ${formatRate(bank.sell)}
                        </strong>

                        ${renderVariation(bank.sell)}

                    </div>

                </div>

            </article>
        `;
    }).join("");
}


/* OPERATION SELECTION */

function setOperation(nextOperation) {
    operation = nextOperation;

    elements.operationButtons.forEach(button => {
        const active =
            button.dataset.operation === operation;

        button.classList.toggle("active", active);

        button.setAttribute(
            "aria-pressed",
            String(active)
        );
    });

    renderBanks();
}


/* ERROR HANDLING */

function showError(error) {
    console.error("Error loading exchange rates:", error);

    elements.connectionStatus.textContent = "Error de conexión";

    elements.bankList.innerHTML = `
        <div class="error-state">
            No fue posible cargar las cotizaciones.
            <br><br>
            Comprueba la disponibilidad de current.json.
        </div>
    `;
}


/* LOAD DATA */

async function loadData() {
    try {
        const response = await fetch(DATA_URL, {
            cache: "no-store",
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        quotes = extractQuotes(data);

        const officialQuote = quotes.find(
            quote => quote.type === "central_bank"
        );

        renderOfficialQuote(officialQuote);

        const updatedAt = data.updated_at;

        elements.updatedAt.textContent = updatedAt
            ? `Actualización: ${formatDate(updatedAt)}`
            : "Actualización: --";

        elements.connectionStatus.textContent = "Datos disponibles";

        renderBanks();

    } catch (error) {
        showError(error);
    }
}


/* EVENTS */

elements.operationButtons.forEach(button => {
    button.addEventListener("click", () => {
        setOperation(button.dataset.operation);
    });
});


/* INITIALIZATION */

loadData();
