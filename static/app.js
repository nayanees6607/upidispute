/**
 * app.js — PaySafe UPI Single-Page Application
 * ──────────────────────────────────────────────
 * SPA router, API client, payment flow state machine,
 * toast notifications, and all view rendering logic.
 */

// ═══════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════
let currentUserId = localStorage.getItem("paysafe_user_id");
const API = "";           // Same-origin

// ═══════════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════════
let currentUser = null;
let merchants = [];
let allTransactions = [];
let selectedMerchant = null;
let pinValue = "";
let currentFilter = "all";
let disputedTxnIds = new Set();  // Track transactions that already have disputes

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY HELPERS
// ═══════════════════════════════════════════════════════════════════════════

/** Format number as Indian Rupee */
function formatCurrency(amount) {
    return "₹ " + Number(amount).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

/** Format ISO timestamp to friendly string */
function formatTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;

    // If within the last 24h, show relative
    if (diff < 86400000) {
        if (diff < 60000) return "Just now";
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        return `${Math.floor(diff / 3600000)}h ago`;
    }
    // Otherwise show date
    return d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

/** Status to CSS class mapping */
function statusClass(status) {
    return (status || "").toLowerCase().replace(/_/g, "");
}

/** Show a toast notification */
function toast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "✕" : "⚠"}</span> ${message}`;
    container.appendChild(el);
    setTimeout(() => {
        el.classList.add("removing");
        setTimeout(() => el.remove(), 300);
    }, 3500);
}

// ═══════════════════════════════════════════════════════════════════════════
// API CLIENT
// ═══════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════

async function authLogin(phone, pin) {
    const res = await fetch(`${API}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, pin })
    });
    return res.json();
}

async function authRegister(name, phone, email, balance, pin) {
    const res = await fetch(`${API}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, phone, email, balance, pin })
    });
    return res.json();
}

async function fetchUser() {
    if (!currentUserId) return null;
    const res = await fetch(`${API}/api/user/${currentUserId}`);
    currentUser = await res.json();
    return currentUser;
}

async function fetchMerchants() {
    const res = await fetch(`${API}/api/merchants`);
    merchants = await res.json();
    return merchants;
}

async function fetchTransactions() {
    if (!currentUserId) return [];
    const res = await fetch(`${API}/api/transactions/${currentUserId}`);
    allTransactions = await res.json();
    return allTransactions;
}

async function makePayment(merchantId, amount, pin) {
    const res = await fetch(`${API}/api/pay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            user_id: currentUserId,
            merchant_id: merchantId,
            amount: amount,
            pin: pin,
        }),
    });
    return res.json();
}

async function raiseDispute(txnId, reason = "") {
    const res = await fetch(`${API}/api/disputes/raise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ txn_id: txnId, reason: reason }),
    });
    return res.json();
}

async function fetchDisputes() {
    const res = await fetch(`${API}/api/disputes/status`);
    return res.json();
}

async function runAgent() {
    const res = await fetch(`${API}/api/agent/run`, { method: "POST" });
    return res.json();
}

// ═══════════════════════════════════════════════════════════════════════════
// SPA ROUTER
// ═══════════════════════════════════════════════════════════════════════════

function switchView(viewName) {
    const currentView = document.querySelector(".view.active");
    const target = document.getElementById(`view-${viewName}`);
    if (!target || target === currentView) return;

    // Deactivate all nav links
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    const navLink = document.querySelector(`.nav-link[data-view="${viewName}"]`);
    if (navLink) navLink.classList.add("active");

    // If there's a current view, animate it out first
    if (currentView) {
        currentView.classList.add("exiting");
        currentView.addEventListener("animationend", function handler() {
            currentView.removeEventListener("animationend", handler);
            currentView.classList.remove("active", "exiting");
            // Show & animate in the new view
            showNewView(target, viewName);
        }, { once: true });
    } else {
        showNewView(target, viewName);
    }
}

function showNewView(target, viewName) {
    target.classList.add("active");
    // Re-trigger entrance animation
    target.style.animation = "none";
    target.offsetHeight;
    target.style.animation = "";

    // Re-trigger staggered children animations
    retriggerAnimations(target);

    // Refresh data for the view
    if (viewName === "home") refreshHome();
    if (viewName === "history") refreshHistory();
    if (viewName === "disputes") refreshDisputes();
}

/** Re-trigger CSS animations on animated children (merchant cards, txn items, etc.) */
function retriggerAnimations(container) {
    const animated = container.querySelectorAll(
        ".merchant-card, .txn-item, .dispute-card, .agent-result-item, .balance-card, .pay-section"
    );
    animated.forEach(el => {
        el.style.animation = "none";
        el.offsetHeight;
        el.style.animation = "";
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// HOME VIEW
// ═══════════════════════════════════════════════════════════════════════════

async function refreshHome() {
    const [_user, _merchants, _txns, disputes] = await Promise.all([
        fetchUser(), fetchMerchants(), fetchTransactions(), fetchDisputes()
    ]);
    // Pre-populate disputed transaction IDs
    if (Array.isArray(disputes)) {
        disputes.forEach(d => disputedTxnIds.add(d.txn_id));
    }
    renderHomeBalance();
    renderMerchants();
    renderHomeTransactions();
}

function renderHomeBalance() {
    if (!currentUser) return;
    document.getElementById("home-username").textContent = currentUser.name;
    document.getElementById("home-balance").textContent = formatCurrency(currentUser.balance);
    document.getElementById("home-upi").textContent = currentUser.upi_id;
    document.getElementById("nav-avatar").textContent = currentUser.name.charAt(0).toUpperCase();
}

function renderMerchants() {
    const grid = document.getElementById("merchants-grid");
    grid.innerHTML = merchants.map(m => `
        <div class="merchant-card" data-merchant-id="${m.merchant_id}" id="merchant-${m.merchant_id}">
            <div class="merchant-icon" style="background: ${m.color}22">
                ${m.icon}
            </div>
            <div class="merchant-name">${m.name}</div>
            <div class="merchant-category">${m.category}</div>
        </div>
    `).join("");

    // Attach click handlers
    grid.querySelectorAll(".merchant-card").forEach(card => {
        card.addEventListener("click", () => {
            const id = card.dataset.merchantId;
            selectedMerchant = merchants.find(m => m.merchant_id === id);
            openPayDrawer();
        });
    });
}

function renderHomeTransactions() {
    const container = document.getElementById("home-transactions");
    const recent = allTransactions.slice(0, 5);

    if (recent.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">💸</div>
                <h3>No transactions yet</h3>
                <p>Make your first payment!</p>
            </div>`;
        return;
    }

    container.innerHTML = recent.map(txn => renderTxnItem(txn, false)).join("");
}

/** Render a single transaction row */
function renderTxnItem(txn, showActions = false) {
    const statusCls = statusClass(txn.status);
    const canDispute = (txn.status === "DEBITED" || txn.status === "FAILED") && !disputedTxnIds.has(txn.txn_id);
    const alreadyDisputed = disputedTxnIds.has(txn.txn_id);
    let actionHtml = "";
    if (showActions && canDispute) {
        actionHtml = `<div class="txn-actions">
            <button class="btn-dispute" data-txn-id="${txn.txn_id}" id="dispute-btn-${txn.txn_id}">🛡️ Raise Dispute</button>
        </div>`;
    } else if (showActions && alreadyDisputed) {
        actionHtml = `<div class="txn-actions">
            <span class="btn-dispute raised" style="opacity:0.6;pointer-events:none;">🛡️ Dispute Raised</span>
        </div>`;
    }

    return `
        <div class="txn-item ${showActions ? "with-actions" : ""}" id="txn-${txn.txn_id}">
            <div class="txn-icon" style="background: ${txn.status === "SUCCESS" ? "var(--success-bg)" : txn.status === "FAILED" ? "var(--error-bg)" : "var(--warning-bg)"}">
                ${txn.status === "SUCCESS" ? "✓" : txn.status === "FAILED" ? "✕" : txn.status === "REFUNDED" ? "↩" : "⏳"}
            </div>
            <div class="txn-details">
                <div class="txn-name">${txn.merchant_name || txn.merchant_id}</div>
                <div class="txn-time">${formatTime(txn.timestamp)}</div>
            </div>
            <div class="txn-right">
                <div class="txn-amount debit">- ${formatCurrency(txn.amount)}</div>
                <div class="txn-status-badge ${statusCls}">${txn.status}</div>
            </div>
            ${actionHtml}
        </div>`;
}

// ═══════════════════════════════════════════════════════════════════════════
// PAY FLOW
// ═══════════════════════════════════════════════════════════════════════════

function openPayDrawer() {
    if (!selectedMerchant) return;

    // Set merchant info
    document.getElementById("pay-merchant-icon").textContent = selectedMerchant.icon;
    document.getElementById("pay-merchant-icon").style.background = selectedMerchant.color + "22";
    document.getElementById("pay-merchant-name").textContent = selectedMerchant.name;
    document.getElementById("pay-merchant-upi").textContent = selectedMerchant.upi_id;
    document.getElementById("pay-amount").value = "";

    // Reset to step 1
    showPayStep(1);
    pinValue = "";
    updatePinDots();

    // Show overlay
    document.getElementById("pay-overlay").classList.remove("hidden");

    // Focus amount input after animation
    setTimeout(() => document.getElementById("pay-amount").focus(), 400);
}

function closePayDrawer() {
    const overlay = document.getElementById("pay-overlay");
    overlay.classList.add("closing");
    // Wait for close animation to finish before hiding
    overlay.addEventListener("animationend", function handler(e) {
        if (e.target === overlay || e.target.classList.contains("pay-drawer")) {
            overlay.removeEventListener("animationend", handler);
            overlay.classList.add("hidden");
            overlay.classList.remove("closing");
            selectedMerchant = null;
        }
    }, { once: true });
    // Fallback in case animation event doesn't fire
    setTimeout(() => {
        if (!overlay.classList.contains("hidden")) {
            overlay.classList.add("hidden");
            overlay.classList.remove("closing");
            selectedMerchant = null;
        }
    }, 400);
}

function showPayStep(step) {
    document.querySelectorAll(".pay-step").forEach(s => s.classList.remove("active"));
    const target = document.getElementById(`pay-step-${step}`);
    if (target) target.classList.add("active");
}

function updatePinDots() {
    const dots = document.querySelectorAll("#pin-dots .pin-dot");
    dots.forEach((dot, i) => {
        dot.classList.toggle("filled", i < pinValue.length);
    });
}

async function submitPayment() {
    const amount = parseFloat(document.getElementById("pay-amount").value);
    if (!selectedMerchant || !amount || amount <= 0) return;

    try {
        const result = await makePayment(selectedMerchant.merchant_id, amount, pinValue);

        if (result.error) {
            // Show error result
            showPayResult("error", result.error, amount, selectedMerchant.name, "");
            return;
        }

        const txn = result.transaction;
        const status = txn.status;

        if (status === "SUCCESS") {
            showPayResult("success", "Payment Successful!", txn.amount, selectedMerchant.name, txn.txn_id, status);
            toast(`Paid ${formatCurrency(txn.amount)} to ${selectedMerchant.name}`, "success");
        } else if (status === "DEBITED") {
            showPayResult("debited", "Payment Processing", txn.amount, selectedMerchant.name, txn.txn_id, status);
            toast("Money debited but not confirmed yet", "warning");
        } else {
            showPayResult("failed", "Payment Failed", txn.amount, selectedMerchant.name, txn.txn_id, status);
            toast("Transaction failed — no money deducted", "error");
        }

        // Update balance
        if (result.new_balance !== undefined) {
            currentUser.balance = result.new_balance;
            renderHomeBalance();
        }

        // Refresh notifications (new notification was created server-side)
        refreshNotifications();

    } catch (err) {
        showPayResult("error", "Network Error", 0, "", "");
        toast("Something went wrong. Try again.", "error");
    }
}

function showPayResult(type, title, amount, merchantName, txnId, status = "") {
    showPayStep(3);

    const icon = document.getElementById("result-icon");
    icon.className = "result-icon";

    if (type === "success") {
        icon.classList.add("success");
        icon.textContent = "✓";
    } else if (type === "failed" || type === "error") {
        icon.classList.add("failed");
        icon.textContent = "✕";
    } else if (type === "debited") {
        icon.classList.add("debited");
        icon.textContent = "⏳";
    }

    // Re-trigger animation
    icon.style.animation = "none";
    icon.offsetHeight;
    icon.style.animation = "";

    document.getElementById("result-title").textContent = title;
    document.getElementById("result-amount").textContent = formatCurrency(amount);
    document.getElementById("result-to").textContent = merchantName ? `to ${merchantName}` : "";
    document.getElementById("result-txn").textContent = txnId ? `TXN ID: ${txnId}` : "";

    const badge = document.getElementById("result-status-badge");
    badge.textContent = status || type.toUpperCase();
    badge.className = "result-status-badge " + statusClass(status || type);
}

// ═══════════════════════════════════════════════════════════════════════════
// HISTORY VIEW
// ═══════════════════════════════════════════════════════════════════════════

async function refreshHistory() {
    await fetchTransactions();
    renderHistory();
}

function renderHistory() {
    const container = document.getElementById("history-transactions");
    let filtered = allTransactions;

    if (currentFilter !== "all") {
        filtered = allTransactions.filter(t => t.status === currentFilter);
    }

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h3>No transactions found</h3>
                <p>No ${currentFilter === "all" ? "" : currentFilter.toLowerCase() + " "}transactions to show</p>
            </div>`;
        return;
    }

    container.innerHTML = filtered.map(txn => renderTxnItem(txn, true)).join("");

    // Attach dispute buttons
    container.querySelectorAll(".btn-dispute").forEach(btn => {
        btn.addEventListener("click", async () => {
            const txnId = btn.dataset.txnId;
            const reason = prompt("Why are you raising this dispute?", "Money debited but service/product not received");
            if (reason === null) return; // User cancelled
            btn.disabled = true;
            btn.textContent = "🤖 Analyzing…";
            try {
                const result = await raiseDispute(txnId, reason);
                if (result.error) {
                    toast(result.error || result.message, "error");
                    btn.textContent = "🛡️ Raise Dispute";
                    btn.disabled = false;
                    return;
                }
                disputedTxnIds.add(txnId);
                const status = result.dispute?.current_status || "PROCESSING";
                if (status === "RESOLVED") {
                    toast(`Dispute auto-resolved for ${txnId}`, "success");
                } else {
                    toast(`Dispute raised for ${txnId} — Status: ${status}`, "success");
                }
                // Refresh balance (may have changed due to refund)
                fetchUser().then(renderHomeBalance);
                // Refresh notifications
                refreshNotifications();
            } catch {
                toast("Failed to raise dispute", "error");
            }
            btn.textContent = "🛡️ Raised";
            btn.style.opacity = "0.6";
            btn.style.pointerEvents = "none";
        });
    });
}

// ═══════════════════════════════════════════════════════════════════════════
// DISPUTES VIEW
// ═══════════════════════════════════════════════════════════════════════════

async function refreshDisputes() {
    const disputes = await fetchDisputes();
    const container = document.getElementById("disputes-list");
    const empty = document.getElementById("disputes-empty");

    if (disputes.length === 0) {
        container.innerHTML = "";
        empty.classList.remove("hidden");
        return;
    }

    empty.classList.add("hidden");
    container.innerHTML = disputes.map(d => {
        const statusCls = statusClass(d.current_status);
        const txn = d.transaction;

        return `
            <div class="dispute-card" id="dispute-${d.dispute_id}">
                <div class="dispute-header">
                    <div class="dispute-id">Dispute #${d.dispute_id} · ${d.txn_id}</div>
                    <div class="dispute-status ${statusCls}">${d.current_status}</div>
                </div>
                <div class="dispute-txn-info">
                    <strong>${txn ? txn.merchant_name || txn.merchant_id : "—"}</strong>
                    · ${txn ? formatCurrency(txn.amount) : "—"}
                    · Bank: ${txn ? txn.status : "—"}
                </div>
                ${d.user_reason ? `<div class="dispute-reason"><strong>Your Reason:</strong> ${d.user_reason}</div>` : ""}
                ${d.admin_reason ? `<div class="dispute-reason admin"><strong>Admin Response:</strong> ${d.admin_reason}</div>` : ""}
            </div>`;
    }).join("");
}


// ═══════════════════════════════════════════════════════════════════════════
// NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════════════════

async function fetchNotifications() {
    if (!currentUserId) return [];
    const res = await fetch(`${API}/api/notifications/${currentUserId}`);
    return res.json();
}

async function markAllNotificationsRead() {
    if (!currentUserId) return;
    const res = await fetch(`${API}/api/notifications/${currentUserId}/read-all`, { method: "POST" });
    return res.json();
}

function renderNotifications(data) {
    const badge = document.getElementById("notif-badge");
    const list = document.getElementById("notif-list");

    // Update badge
    if (data.unread_count > 0) {
        badge.textContent = data.unread_count > 9 ? "9+" : data.unread_count;
        badge.classList.remove("hidden");
    } else {
        badge.classList.add("hidden");
    }

    // Render list
    if (!data.notifications || data.notifications.length === 0) {
        list.innerHTML = '<div class="notif-empty">No notifications yet</div>';
        return;
    }

    const typeIcons = {
        PAYMENT: "💳",
        DISPUTE: "🛡️",
        REFUND: "💰",
        INFO: "ℹ️",
    };

    list.innerHTML = data.notifications.map(n => {
        const icon = typeIcons[n.notif_type] || "📢";
        const readCls = n.is_read ? "read" : "unread";
        return `
            <div class="notif-item ${readCls}">
                <div class="notif-icon">${icon}</div>
                <div class="notif-content">
                    <div class="notif-item-title">${n.title}</div>
                    <div class="notif-item-msg">${n.message}</div>
                    <div class="notif-item-time">${formatTime(n.created_at)}</div>
                </div>
            </div>`;
    }).join("");
}

async function refreshNotifications() {
    try {
        const data = await fetchNotifications();
        renderNotifications(data);
    } catch { /* silent */ }
}

// ═══════════════════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
    // ── Navigation ────────────────────────────────────────────────────
    document.querySelectorAll(".nav-link, .see-all").forEach(link => {
        link.addEventListener("click", e => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view) switchView(view);
        });
    });

    // ── Pay Button (center circle) ────────────────────────────────────
    document.getElementById("btn-pay").addEventListener("click", () => {
        // Open pay with first merchant selected, or show merchant selection
        if (merchants.length > 0) {
            selectedMerchant = merchants[0];
            openPayDrawer();
        }
    });

    // ── Pay Drawer Controls ───────────────────────────────────────────
    document.getElementById("pay-close").addEventListener("click", closePayDrawer);

    document.getElementById("pay-overlay").addEventListener("click", e => {
        if (e.target.id === "pay-overlay") closePayDrawer();
    });

    document.getElementById("btn-proceed-pin").addEventListener("click", () => {
        const amount = parseFloat(document.getElementById("pay-amount").value);
        if (!amount || amount <= 0) {
            toast("Please enter a valid amount", "warning");
            return;
        }
        if (currentUser && amount > currentUser.balance) {
            toast("Insufficient balance", "error");
            return;
        }
        pinValue = "";
        updatePinDots();
        showPayStep(2);
    });

    document.getElementById("pin-back").addEventListener("click", () => {
        pinValue = "";
        updatePinDots();
        showPayStep(1);
    });

    // ── PIN Keypad ────────────────────────────────────────────────────
    document.getElementById("pin-keypad").addEventListener("click", e => {
        const btn = e.target.closest(".key");
        if (!btn) return;

        const key = btn.dataset.key;
        if (!key) return;

        if (key === "del") {
            pinValue = pinValue.slice(0, -1);
        } else if (pinValue.length < 4) {
            pinValue += key;
        }

        updatePinDots();

        // Auto-submit when 4 digits entered
        if (pinValue.length === 4) {
            setTimeout(() => submitPayment(), 200);
        }
    });

    // ── Done Button ───────────────────────────────────────────────────
    document.getElementById("btn-done").addEventListener("click", () => {
        closePayDrawer();
        // Refresh data
        refreshHome();
    });

    // ── Filter Chips ──────────────────────────────────────────────────
    document.getElementById("filter-bar").addEventListener("click", e => {
        const chip = e.target.closest(".filter-chip");
        if (!chip) return;
        document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        currentFilter = chip.dataset.filter;
        renderHistory();
    });

    // ── Run Agent Button ──────────────────────────────────────────────

    // ── Notification Bell ─────────────────────────────────────────────
    document.getElementById("notif-bell").addEventListener("click", (e) => {
        e.stopPropagation();
        const dropdown = document.getElementById("notif-dropdown");

        dropdown.classList.toggle("hidden");

        if (!dropdown.classList.contains("hidden")) {
            refreshNotifications();
        }
    });

    document.getElementById("notif-mark-read").addEventListener("click", async () => {
        await markAllNotificationsRead();
        await refreshNotifications();
        toast("All notifications marked as read", "success");
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
        const wrapper = document.getElementById("notif-wrapper");
        const dropdown = document.getElementById("notif-dropdown");

        if (!wrapper.contains(e.target)) {
            dropdown.classList.add("hidden");
        }
    });

    // ── Auth UI Toggles ───────────────────────────────────────────────
    document.getElementById("show-register").addEventListener("click", (e) => {
        e.preventDefault();
        document.getElementById("login-form").classList.add("hidden");
        document.getElementById("register-form").classList.remove("hidden");
    });

    document.getElementById("show-login").addEventListener("click", (e) => {
        e.preventDefault();
        document.getElementById("register-form").classList.add("hidden");
        document.getElementById("login-form").classList.remove("hidden");
    });

    // ── Login Submit ──────────────────────────────────────────────────
    document.getElementById("login-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const phone = document.getElementById("login-phone").value;
        const pin = document.getElementById("login-pin").value;

        try {
            const result = await authLogin(phone, pin);
            if (result.error) {
                toast(result.error, "error");
                return;
            }
            handleAuthSuccess(result.user);
        } catch (err) {
            toast("Login failed", "error");
        }
    });

    // ── Register Submit ───────────────────────────────────────────────
    document.getElementById("register-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("reg-name").value;
        const phone = document.getElementById("reg-phone").value;
        const email = document.getElementById("reg-email").value;
        const balance = document.getElementById("reg-balance").value;
        const pin = document.getElementById("reg-pin").value;

        try {
            const result = await authRegister(name, phone, email, balance, pin);
            if (result.error) {
                toast(result.error, "error");
                return;
            }
            handleAuthSuccess(result.user);
        } catch (err) {
            toast("Registration failed", "error");
        }
    });

    // ── Logout ───────────────────────────────────────────────────────
    document.getElementById("nav-logout").addEventListener("click", () => {
        // Clear session
        localStorage.removeItem("paysafe_user_id");
        currentUserId = null;
        currentUser = null;

        // Show auth, hide app
        document.getElementById("main-app-view").classList.add("hidden");
        document.getElementById("auth-view").classList.remove("hidden");

        // Reset forms
        document.getElementById("login-form").reset();
        document.getElementById("register-form").reset();
        document.getElementById("register-form").classList.add("hidden");
        document.getElementById("login-form").classList.remove("hidden");

        // Close dropdown
        document.getElementById("notif-dropdown").classList.add("hidden");

        // Stop polling (by clearing interval or just letting it fail gracefully)
        toast("Logged out successfully");
    });

    // ── Initial Load Logic ────────────────────────────────────────────
    function handleAuthSuccess(user) {
        currentUserId = user.user_id;
        localStorage.setItem("paysafe_user_id", currentUserId);

        document.getElementById("auth-view").classList.add("hidden");
        document.getElementById("main-app-view").classList.remove("hidden");

        refreshHome();
        refreshNotifications();
        toast(`Welcome, ${user.name}!`);
    }

    // Check session on load
    if (currentUserId) {
        // Hydrate app immediately
        document.getElementById("auth-view").classList.add("hidden");
        document.getElementById("main-app-view").classList.remove("hidden");
        refreshHome();
        refreshNotifications();
    } else {
        // Show login natively
        document.getElementById("main-app-view").classList.add("hidden");
        document.getElementById("auth-view").classList.remove("hidden");
    }

    // Poll for new notifications every 30 seconds
    setInterval(() => {
        if (currentUserId) refreshNotifications();
    }, 30000);
});
