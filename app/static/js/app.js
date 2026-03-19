"use strict";

const STATUS_LABELS = {
    unpaid: "Unpaid",
    partially_paid: "Partially paid",
    paid: "Paid",
};

const STATUS_CLASSES = {
    unpaid: "badge--muted",
    partially_paid: "badge--warn",
    paid: "badge--ok",
};

function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleString("ru-RU", {
        day: "2-digit", month: "2-digit", year: "numeric",
        hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
}

function formatMoney(v) {
    return Number(v).toFixed(2);
}

let _orders = [];

/* --- Helpers --- */

function buildOrderOptions(filterPaid) {
    const items = filterPaid ? _orders.filter(o => o.payment_status !== "paid") : _orders;
    return '<option value="">-- select order --</option>' +
        items.map(o =>
            `<option value="${o.id}">#${o.number} — ${formatMoney(o.amount_total)} (${STATUS_LABELS[o.payment_status] || o.payment_status})</option>`
        ).join("");
}

function refreshAllSelects() {
    const pairs = [
        ["cash-modal", "cash-order-select", true],
        ["card-modal", "card-order-select", true],
        ["refund-modal", "refund-order-select", false],
    ];
    for (const [modalId, selectId, filterPaid] of pairs) {
        if (!document.getElementById(modalId).hidden) {
            const sel = document.getElementById(selectId);
            const prev = sel.value;
            sel.innerHTML = buildOrderOptions(filterPaid);
            sel.value = prev;
        }
    }
}

function refreshRefundPayments() {
    if (document.getElementById("refund-modal").hidden) return;
    const orderId = document.getElementById("refund-order-select").value;
    if (orderId) loadPaymentsForOrder(orderId);
}

function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg;
}

function clearError(id) {
    const el = document.getElementById(id);
    if (el) el.textContent = "";
}

async function extractError(res, fallback) {
    try {
        const data = await res.json();
        return data.detail || fallback;
    } catch {
        return fallback;
    }
}

/* --- Orders --- */

function renderOrders(orders) {
    const container = document.getElementById("orders-list");
    if (!orders.length) {
        container.innerHTML = '<p class="empty">No orders yet</p>';
        return;
    }

    const rows = orders.map(o => `
        <tr>
            <td class="cell--mono">${o.number}</td>
            <td class="cell--right">${formatMoney(o.amount_total)}</td>
            <td class="cell--right">${formatMoney(o.paid_amount)}</td>
            <td class="cell--right">${formatMoney(o.refunded_amount)}</td>
            <td><span class="badge ${STATUS_CLASSES[o.payment_status] || ""}">${STATUS_LABELS[o.payment_status] || o.payment_status}</span></td>
            <td class="cell--muted">${formatDate(o.created_at)}</td>
        </tr>
    `).join("");

    container.innerHTML = `
        <table class="table">
            <thead>
                <tr>
                    <th>Number</th>
                    <th class="cell--right">Total</th>
                    <th class="cell--right">Paid</th>
                    <th class="cell--right">Refunded</th>
                    <th>Status</th>
                    <th>Created</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

async function loadOrders() {
    try {
        const res = await fetch("/orders");
        const data = await res.json();
        _orders = data.items;
        renderOrders(data.items);
    } catch (err) {
        document.getElementById("orders-list").innerHTML =
            '<p class="empty empty--error">Failed to load orders</p>';
    }
}

/* --- Logs --- */

function statusBadge(payload) {
    if (!payload || !payload.status_code) return "";
    const code = payload.status_code;
    let cls = "log-row__status--ok";
    if (code >= 500) cls = "log-row__status--error";
    else if (code >= 400) cls = "log-row__status--warn";
    return `<span class="log-row__status ${cls}">${code}</span>`;
}

function renderLogs(logs) {
    const container = document.getElementById("logs-list");
    if (!logs.length) {
        container.innerHTML = '<p class="empty">No logs yet</p>';
        return;
    }

    const rows = logs.map(l => `
        <div class="log-row">
            <span class="log-row__time">${formatDate(l.created_at)}</span>
            <span class="log-row__level log-row__level--${l.level}">${l.level}</span>
            ${statusBadge(l.payload_json)}
            <span class="log-row__source">${l.source}</span>
            <span class="log-row__message">${l.message}</span>
        </div>
    `).join("");

    container.innerHTML = rows;
}

async function loadLogs() {
    try {
        const res = await fetch("/logs?limit=50");
        const data = await res.json();
        renderLogs(data.items);
    } catch (err) {
        document.getElementById("logs-list").innerHTML =
            '<p class="empty empty--error">Failed to load logs</p>';
    }
}

/* --- Create order --- */

async function createOrder(amountTotal) {
    clearError("order-form-error");

    try {
        const res = await fetch("/orders", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount_total: amountTotal }),
        });

        if (!res.ok) {
            showError("order-form-error", await extractError(res, "Failed to create order"));
            return;
        }

        document.getElementById("order-amount").value = "";
        await Promise.all([loadOrders(), loadLogs()]);
        refreshAllSelects();
    } catch {
        showError("order-form-error", "Network error");
    }
}

/* --- Cash payment modal --- */

function openCashModal() {
    const modal = document.getElementById("cash-modal");
    const orderSelect = document.getElementById("cash-order-select");

    clearError("cash-form-error");
    document.getElementById("cash-amount").value = "";

    orderSelect.innerHTML = buildOrderOptions(true);

    modal.hidden = false;
}

function closeCashModal() {
    document.getElementById("cash-modal").hidden = true;
}

async function submitCashPayment() {
    clearError("cash-form-error");

    const orderId = document.getElementById("cash-order-select").value;
    const amount = document.getElementById("cash-amount").value.trim();

    if (!orderId) { showError("cash-form-error", "Select an order"); return; }
    if (!amount)  { showError("cash-form-error", "Enter amount"); return; }

    try {
        const res = await fetch("/payments/cash", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order_id: orderId, amount: amount }),
        });

        if (!res.ok) {
            showError("cash-form-error", await extractError(res, "Payment failed"));
            return;
        }

        closeCashModal();
        await Promise.all([loadOrders(), loadLogs()]);
        refreshAllSelects();
    } catch {
        showError("cash-form-error", "Network error");
    }
}

/* --- Card payment modal --- */

function openCardModal() {
    const modal = document.getElementById("card-modal");
    const orderSelect = document.getElementById("card-order-select");

    clearError("card-form-error");
    document.getElementById("card-amount").value = "";

    orderSelect.innerHTML = buildOrderOptions(true);

    modal.hidden = false;
}

function closeCardModal() {
    document.getElementById("card-modal").hidden = true;
}

async function submitCardPayment() {
    clearError("card-form-error");

    const orderId = document.getElementById("card-order-select").value;
    const amount = document.getElementById("card-amount").value.trim();

    if (!orderId) { showError("card-form-error", "Select an order"); return; }
    if (!amount)  { showError("card-form-error", "Enter amount"); return; }

    try {
        const res = await fetch("/payments/acquiring", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ order_id: orderId, amount: amount }),
        });

        if (!res.ok) {
            showError("card-form-error", await extractError(res, "Payment failed"));
            return;
        }

        closeCardModal();
        await Promise.all([loadOrders(), loadBankPayments(), loadLogs()]);
        refreshAllSelects();
    } catch {
        showError("card-form-error", "Network error");
    }
}

/* --- Bank payments --- */

const BANK_STATUS_CLASSES = {
    received: "badge--blue",
    conducted: "badge--ok",
    cancelled: "badge--danger",
    refunded: "badge--ok",
};

function renderBankPayments(items) {
    const container = document.getElementById("bank-list");
    if (!items.length) {
        container.innerHTML = '<p class="empty">No bank payments yet</p>';
        return;
    }

    const BANK_STATUSES = ["received", "conducted", "cancelled", "refunded"];

    const rows = items.map(b => {
        const options = BANK_STATUSES.map(s =>
            `<option value="${s}" ${s === b.bank_status ? "selected" : ""}>${s}</option>`
        ).join("");

        return `
        <tr>
            <td class="cell--mono cell--muted" title="${b.payment_id}">${b.payment_id.slice(0, 8)}</td>
            <td class="cell--mono cell--muted" title="${b.bank_payment_id}">${b.bank_payment_id.slice(0, 12)}</td>
            <td><span class="badge ${BANK_STATUS_CLASSES[b.bank_status] || "badge--muted"}">${b.bank_status}</span></td>
            <td class="cell--right">${formatMoney(b.bank_amount)}</td>
            <td class="cell--muted">${formatDate(b.last_synced_at)}</td>
            <td class="cell--error">${b.sync_error || ""}</td>
            <td class="cell--actions">
                <select class="select select--sm" id="status-${b.bank_payment_id}">${options}</select>
                <button class="btn btn--sm btn--ghost" onclick="applyBankStatus('${b.bank_payment_id}')">Apply</button>
                <button class="btn btn--sm btn--blue" onclick="syncPayment('${b.payment_id}')">Sync</button>
            </td>
        </tr>`;
    }).join("");

    container.innerHTML = `
        <table class="table">
            <thead>
                <tr>
                    <th>Payment</th>
                    <th>Bank ID</th>
                    <th>Status</th>
                    <th class="cell--right">Amount</th>
                    <th>Synced</th>
                    <th>Error</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

async function loadBankPayments() {
    try {
        const res = await fetch("/bank/payments");
        const data = await res.json();
        renderBankPayments(data.items);
    } catch {
        document.getElementById("bank-list").innerHTML =
            '<p class="empty empty--error">Failed to load bank payments</p>';
    }
}

async function syncPayment(paymentId) {
    clearError("bank-error");

    try {
        const res = await fetch(`/bank/sync/${paymentId}`, { method: "POST" });

        if (!res.ok) {
            showError("bank-error", await extractError(res, "Sync failed"));
            return;
        }

        await Promise.all([loadOrders(), loadBankPayments(), loadLogs()]);
        refreshAllSelects();
        refreshRefundPayments();
    } catch {
        showError("bank-error", "Network error");
    }
}

async function applyBankStatus(bankPaymentId) {
    clearError("bank-error");

    const selectEl = document.getElementById(`status-${bankPaymentId}`);
    if (!selectEl) return;

    const newStatus = selectEl.value;

    try {
        const res = await fetch(`/mock-bank/payments/${bankPaymentId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bank_status: newStatus }),
        });

        if (!res.ok) {
            showError("bank-error", await extractError(res, "Status update failed"));
            return;
        }

        await Promise.all([loadBankPayments(), loadLogs()]);
    } catch {
        showError("bank-error", "Network error");
    }
}

/* --- Refund modal --- */

const PAYMENT_STATUS_LABELS = {
    pending: "Pending",
    completed: "Completed",
    cancelled: "Cancelled",
    part_refunded: "Part refunded",
    refunded: "Refunded",
    failed: "Failed",
};

function openRefundModal() {
    const modal = document.getElementById("refund-modal");
    const orderSelect = document.getElementById("refund-order-select");
    const paymentSelect = document.getElementById("refund-payment-select");

    clearError("refund-form-error");
    document.getElementById("refund-amount").value = "";
    paymentSelect.innerHTML = '<option value="">-- select payment --</option>';

    orderSelect.innerHTML = buildOrderOptions(false);

    modal.hidden = false;
}

function closeRefundModal() {
    document.getElementById("refund-modal").hidden = true;
}

async function loadPaymentsForOrder(orderId) {
    const paymentSelect = document.getElementById("refund-payment-select");
    paymentSelect.innerHTML = '<option value="">Loading...</option>';

    try {
        const res = await fetch(`/orders/${orderId}/payments`);
        const data = await res.json();

        if (!data.items.length) {
            paymentSelect.innerHTML = '<option value="">No payments</option>';
            return;
        }

        paymentSelect.innerHTML = '<option value="">-- select payment --</option>' +
            data.items.map(p =>
                `<option value="${p.id}">${p.payment_type} — ${formatMoney(p.amount)} (${PAYMENT_STATUS_LABELS[p.status] || p.status})</option>`
            ).join("");
    } catch {
        paymentSelect.innerHTML = '<option value="">Failed to load</option>';
    }
}

async function submitRefund() {
    clearError("refund-form-error");

    const orderId = document.getElementById("refund-order-select").value;
    const paymentId = document.getElementById("refund-payment-select").value;
    const amount = document.getElementById("refund-amount").value.trim();

    if (!orderId)   { showError("refund-form-error", "Select an order"); return; }
    if (!paymentId) { showError("refund-form-error", "Select a payment"); return; }
    if (!amount)    { showError("refund-form-error", "Enter amount"); return; }

    try {
        const res = await fetch("/refunds", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ payment_id: paymentId, amount: amount }),
        });

        if (!res.ok) {
            showError("refund-form-error", await extractError(res, "Refund failed"));
            return;
        }

        closeRefundModal();
        await Promise.all([loadOrders(), loadBankPayments(), loadLogs()]);
        refreshAllSelects();
    } catch {
        showError("refund-form-error", "Network error");
    }
}

/* --- Bank mode --- */

function renderBankMode(online) {
    const toggle = document.getElementById("bank-mode-toggle");
    const label = document.getElementById("bank-mode-label");
    toggle.checked = online;
    label.textContent = online ? "Online" : "Offline";
    label.className = online ? "toggle__label" : "toggle__label toggle__label--off";
}

async function loadBankMode() {
    try {
        const res = await fetch("/mock-bank/mode");
        const data = await res.json();
        renderBankMode(data.online);
    } catch { /* ignore */ }
}

async function setBankMode(online) {
    clearError("bank-mode-error");

    try {
        const res = await fetch("/mock-bank/mode", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ online }),
        });

        if (!res.ok) {
            showError("bank-mode-error", await extractError(res, "Failed to switch mode"));
            return;
        }

        const data = await res.json();
        renderBankMode(data.online);
        await loadLogs();
    } catch {
        showError("bank-mode-error", "Failed to switch mode");
    }
}

/* --- Init --- */

document.addEventListener("DOMContentLoaded", () => {
    loadOrders();
    loadBankPayments();
    loadBankMode();
    loadLogs();

    document.getElementById("create-order-form").addEventListener("submit", (e) => {
        e.preventDefault();
        const amount = document.getElementById("order-amount").value.trim();
        if (amount) createOrder(amount);
    });

    document.getElementById("bank-mode-toggle").addEventListener("change", (e) => {
        setBankMode(e.target.checked);
    });

    document.getElementById("open-cash-btn").addEventListener("click", openCashModal);
    document.getElementById("confirm-cash-btn").addEventListener("click", submitCashPayment);
    document.getElementById("cancel-cash-btn").addEventListener("click", closeCashModal);

    document.getElementById("open-card-btn").addEventListener("click", openCardModal);
    document.getElementById("confirm-card-btn").addEventListener("click", submitCardPayment);
    document.getElementById("cancel-card-btn").addEventListener("click", closeCardModal);

    document.getElementById("open-refund-btn").addEventListener("click", openRefundModal);
    document.getElementById("confirm-refund-btn").addEventListener("click", submitRefund);
    document.getElementById("cancel-refund-btn").addEventListener("click", closeRefundModal);

    document.querySelectorAll(".modal__backdrop").forEach(el =>
        el.addEventListener("click", () => {
            closeCashModal();
            closeCardModal();
            closeRefundModal();
        })
    );

    document.getElementById("refund-order-select").addEventListener("change", (e) => {
        const orderId = e.target.value;
        const paymentSelect = document.getElementById("refund-payment-select");
        if (orderId) {
            loadPaymentsForOrder(orderId);
        } else {
            paymentSelect.innerHTML = '<option value="">-- select payment --</option>';
        }
    });
});
