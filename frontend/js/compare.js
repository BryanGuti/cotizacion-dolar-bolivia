const byId = id => document.getElementById(id);
const baseBankSelect = document.getElementById("base-bank");
const elements = {
    selects: [baseBankSelect, document.getElementById("compare-bank")],
    operationButtons: document.querySelectorAll("[data-operation]"),
    status: byId("compare-status"),
    official: byId("compare-official"),
    officialDate: byId("compare-official-date"),
    updated: byId("compare-updated"),
    details: byId("comparison-details"),
    amount: byId("usd-amount"),
    heading: byId("calculation-heading"),
};
const state = { data: null, operation: "buy", selected: ["", ""] };
const rateFormatter = new Intl.NumberFormat("es-BO", { minimumFractionDigits: 2, maximumFractionDigits: 4 });
const formatMoney = value => Number.isFinite(value) ? `${rateFormatter.format(value)} Bs.` : "--";
const formatSignedMoney = value => Number.isFinite(value) ? `${value > 0 ? "+" : value < 0 ? "−" : ""}${rateFormatter.format(Math.abs(value))} Bs.` : "--";
const formatSignedPercent = value => Number.isFinite(value) ? `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(2)}%` : "--";

function formatDate(value) {
    if (!value) return "--";
    const date = new Date(`${value}T12:00:00`);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("es-BO", { day: "2-digit", month: "short", year: "numeric", timeZone: "America/La_Paz" }).format(date);
}

function formatDateTime(value) {
    if (!value) return "--";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "--" : new Intl.DateTimeFormat("es-BO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "America/La_Paz" }).format(date);
}

function populateEntities() {
    const requestedId = new URLSearchParams(location.search).get("entity") || "";
    elements.selects.forEach((select, index) => {
        select.replaceChildren(new Option("Selecciona un banco", ""), ...state.data.entities.map(entity => new Option(entity.name, entity.id)));
        state.selected[index] = index === 0 && state.data.entities.some(entity => entity.id === requestedId) ? requestedId : "";
        select.value = state.selected[index];
    });
}

function showEntity(entity, index) {
    const prefix = index === 0 ? "base-bank" : "compare-bank";
    byId(`${prefix}-name`).textContent = entity?.name || (index === 0 ? "Selecciona un banco" : "Selecciona otro banco");
    byId(`${prefix}-date`).textContent = `Fecha: ${formatDate(entity?.date)}`;
    byId(`${prefix}-buy`).textContent = formatMoney(entity?.buy);
    byId(`${prefix}-sell`).textContent = formatMoney(entity?.sell);
    byId(`${prefix}-buy`).classList.toggle("is-rate-active", state.operation === "sell");
    byId(`${prefix}-sell`).classList.toggle("is-rate-active", state.operation === "buy");
}

function createCard({ category, title, value, formula, note, tone = "neutral", featured = false }) {
    const card = document.createElement("article");
    card.className = `calculation-card calculation-card--${category}${featured ? " calculation-card--featured" : ""}`;
    const eyebrow = document.createElement("p");
    eyebrow.className = "calculation-card__category";
    eyebrow.textContent = category === "comparison" ? "Diferencia entre bancos" : category === "official" ? "Frente al BCB" : "Total estimado";
    const heading = document.createElement("h3");
    heading.textContent = title;
    const number = document.createElement("strong");
    number.className = `calculation-card__value is-${tone}`;
    number.textContent = value;
    const explanation = document.createElement("p");
    explanation.className = "calculation-card__formula";
    explanation.textContent = formula;
    const noteElement = document.createElement("p");
    noteElement.className = "calculation-card__note";
    noteElement.textContent = note;
    card.append(eyebrow, heading, number, explanation, noteElement);
    return card;
}

function signedTone(value, goodWhenPositive = true) {
    if (Math.abs(value) < 0.000001) return "neutral";
    return (value > 0) === goodWhenPositive ? "positive" : "negative";
}

function renderComparison() {
    if (!state.data) return;
    const banks = state.selected.map(id => state.data.entities.find(entity => entity.id === id) || null);
    banks.forEach(showEntity);

    const amount = elements.amount.valueAsNumber;
    const amountIsValid = Number.isFinite(amount) && amount > 0 && elements.amount.validity.valid;
    const bothBanksSelected = Boolean(banks[0] && banks[1]);
    const ready = amountIsValid && bothBanksSelected;
    const buying = state.operation === "buy";
    const operationName = buying ? "comprar" : "vender";
    const operationRateName = buying ? "venta" : "compra";
    const rateKey = buying ? "sell" : "buy";
    elements.amount.setAttribute("aria-invalid", String(!amountIsValid));
    elements.heading.textContent = `Resultados para ${amountIsValid ? rateFormatter.format(amount) : "--"} USD · ${buying ? "Compra de dólares" : "Venta de dólares"}`;

    if (!ready) {
        elements.details.replaceChildren(
            createCard({ category: "comparison", title: "Diferencia en bolivianos", value: "-- Bs.", formula: "Elige dos bancos e ingresa una cantidad válida.", note: "La diferencia se calculará para la operación seleccionada.", featured: true }),
            createCard({ category: "comparison", title: "Diferencia porcentual", value: "--%", formula: "Se compara el resultado con el banco de referencia.", note: "El signo positivo o negativo indicará si el otro banco resulta más conveniente.", featured: true }),
            ...banks.map((bank, index) => createCard({ category: index === 0 ? "base" : "compare", title: bank ? `${bank.name}: total` : index === 0 ? "Total del banco de referencia" : "Total del banco comparado", value: "-- Bs.", formula: `Cantidad USD × precio de ${operationRateName}.`, note: `Precio usado al ${operationName} dólares: ${bank ? formatMoney(bank[rateKey]) : "--"}.` })),
        );
        elements.status.textContent = !amountIsValid ? "Ingresa una cantidad válida mayor que cero." : "Selecciona dos bancos para calcular la comparación.";
        return;
    }

    const [baseBank, comparedBank] = banks;
    const baseRate = baseBank[rateKey];
    const comparedRate = comparedBank[rateKey];
    const baseTotal = baseRate * amount;
    const comparedTotal = comparedRate * amount;
    // Always show reference-bank total minus comparison-bank total.
    // A negative amount benefits the reference bank when buying; a positive one benefits it when selling.
    const differenceMoney = baseTotal - comparedTotal;
    const differencePercent = baseTotal ? differenceMoney / baseTotal * 100 : 0;
    const comparisonTitle = buying ? "Diferencia de costo" : "Diferencia de dinero recibido";
    const baseIsFavorable = buying ? differenceMoney < 0 : differenceMoney > 0;
    const comparisonMessage = Math.abs(differenceMoney) < 0.005
        ? "Ambos bancos dan prácticamente el mismo resultado."
        : baseIsFavorable
            ? `${baseBank.name} conviene más: ${buying ? "pagarías menos" : "recibirías más"} para ${rateFormatter.format(amount)} USD.`
            : `${comparedBank.name} conviene más: ${buying ? "pagarías menos" : "recibirías más"} para ${rateFormatter.format(amount)} USD.`;

    elements.details.replaceChildren(
        createCard({
            category: "comparison",
            title: comparisonTitle,
            value: formatSignedMoney(differenceMoney),
            formula: `${formatMoney(baseTotal)} del banco de referencia − ${formatMoney(comparedTotal)} del banco comparado.`,
            note: comparisonMessage,
            tone: signedTone(differenceMoney, !buying),
            featured: true,
        }),
        createCard({
            category: "comparison",
            title: "Diferencia porcentual",
            value: formatSignedPercent(differencePercent),
            formula: "La diferencia se calcula sobre el total del banco de referencia.",
            note: comparisonMessage,
            tone: signedTone(differencePercent, !buying),
            featured: true,
        }),
        createCard({
            category: "base",
            title: `${baseBank.name}: total estimado`,
            value: formatMoney(baseTotal),
            formula: `${rateFormatter.format(amount)} USD × ${formatMoney(baseRate)} (${operationRateName}).`,
            note: `Total estimado al ${operationName} dólares.`,
            tone: "base",
        }),
        createCard({
            category: "compare",
            title: `${comparedBank.name}: total estimado`,
            value: formatMoney(comparedTotal),
            formula: `${rateFormatter.format(amount)} USD × ${formatMoney(comparedRate)} (${operationRateName}).`,
            note: `Total estimado al ${operationName} dólares.`,
            tone: "compare",
        }),
    );

    elements.status.textContent = `Comparación lista para ${rateFormatter.format(amount)} USD. El precio aplicado corresponde a ${buying ? "venta" : "compra"} del banco.`;
}

function setOperation(operation) {
    state.operation = operation;
    elements.operationButtons.forEach(button => {
        const active = button.dataset.operation === operation;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
    });
    renderComparison();
}

async function initializeComparePage() {
    try {
        state.data = await DollarData.loadDashboardData();
        elements.official.textContent = formatMoney(state.data.official.official_rate);
        elements.officialDate.textContent = `Fecha: ${formatDate(state.data.official.date)}`;
        elements.updated.textContent = `Actualización: ${formatDateTime(state.data.updatedAt)}`;
        populateEntities();
        renderComparison();
    } catch (error) {
        elements.status.textContent = error.message || "No se pudieron cargar las cotizaciones.";
    }
}

elements.operationButtons.forEach(button => button.addEventListener("click", () => setOperation(button.dataset.operation)));
elements.selects.forEach((select, index) => select.addEventListener("change", () => {
    state.selected[index] = select.value;
    if (state.selected[0] && state.selected[0] === state.selected[1]) {
        const alternative = state.data.entities.find(entity => entity.id !== state.selected[index]);
        state.selected[1 - index] = alternative?.id || "";
        elements.selects[1 - index].value = state.selected[1 - index];
    }
    renderComparison();
}));
elements.amount.addEventListener("input", renderComparison);
document.addEventListener("DOMContentLoaded", initializeComparePage);
