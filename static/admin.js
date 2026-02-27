/**
 * admin.js — PaySafe UPI Admin Dashboard
 * ──────────────────────────────────────────────
 * Logic for the standalone Admin view.
 */

// ═══════════════════════════════════════════════════════════════════════════
// CONSTANTS & UTILITIES
// ═══════════════════════════════════════════════════════════════════════════
const API = "";

function formatTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;

    if (diff < 86400000) {
        if (diff < 60000) return "Just now";
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        return `${Math.floor(diff / 3600000)}h ago`;
    }
    return d.toLocaleDateString("en-IN", {
        day: "numeric", month: "short", year: "numeric",
        hour: "2-digit", minute: "2-digit",
    });
}

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

async function fetchAdminDisputes() {
    const res = await fetch(`${API}/api/admin/disputes`);
    return res.json();
}

async function adminResolve(disputeId, action, reason = "") {
    const res = await fetch(`${API}/api/admin/disputes/${disputeId}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: action, reason: reason })
    });
    return res.json();
}

async function adminReset() {
    const res = await fetch(`${API}/api/admin/reset`, { method: "POST" });
    return res.json();
}

async function fetchAdminTransactions() {
    const res = await fetch(`${API}/api/admin/transactions`);
    return res.json();
}

async function adminUpdateTransactionStatus(txnId, newStatus) {
    const res = await fetch(`${API}/api/admin/transactions/${txnId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
    });
    return res.json();
}

// ═══════════════════════════════════════════════════════════════════════════
// RENDER & LOGIC
// ═══════════════════════════════════════════════════════════════════════════

async function refreshAdmin() {
    try {
        const disputes = await fetchAdminDisputes();
        renderAdminDisputes(disputes);
    } catch (err) {
        toast("Failed to load disputes", "error");
    }
}

function renderAdminDisputes(disputes) {
    const list = document.getElementById("admin-disputes-list");
    const empty = document.getElementById("admin-empty-disputes");

    if (!disputes || disputes.length === 0) {
        list.classList.add("hidden");
        empty.classList.remove("hidden");
        return;
    }

    list.classList.remove("hidden");
    empty.classList.add("hidden");

    list.innerHTML = disputes.map(d => {
        const canResolve = ["MANUAL_REVIEW", "PENDING", "PROCESSING"].includes(d.current_status);
        const isResolved = d.current_status === "RESOLVED";

        let actionHtml = '';
        if (canResolve) {
            actionHtml = `
                <div class="admin-actions" style="flex-direction: column;">
                    <textarea class="admin-reason-input" id="admin-reason-${d.dispute_id}" placeholder="Enter resolution reason..." rows="2" style="width:100%;padding:8px;border-radius:var(--radius-xs);border:1px solid var(--border-light);background:var(--bg-card);color:var(--text-primary);font-family:inherit;font-size:12px;resize:vertical;margin-bottom:8px;"></textarea>
                    <div style="display:flex;gap:10px;">
                        <button class="btn-resolve-approve" data-id="${d.dispute_id}" style="flex:1;">✓ Approve Refund</button>
                        <button class="btn-resolve-reject" data-id="${d.dispute_id}" style="flex:1;">✕ Reject</button>
                    </div>
                </div>
            `;
        } else if (isResolved) {
            actionHtml = `<div class="admin-resolved-label">Resolved${d.admin_reason ? ': ' + d.admin_reason : ''}</div>`;
        }

        return `
            <div class="admin-dispute-card ${canResolve ? 'highlight' : ''}" id="admin-dispute-${d.dispute_id}">
                <div class="admin-card-header">
                    <div>
                        <div class="dispute-id">Dispute #${d.dispute_id}</div>
                        <div class="dispute-txn">TXN: ${d.txn_id}</div>
                    </div>
                    <div class="admin-status-badge ${d.current_status.toLowerCase()}">${d.current_status}</div>
                </div>
                <div class="admin-card-body">
                    <div class="admin-detail-row">
                        <span class="detail-lbl">User:</span>
                        <span class="detail-val">${d.user ? d.user.name : 'Unknown'} (${d.user ? '₹' + d.user.balance.toFixed(2) : ''})</span>
                    </div>
                    <div class="admin-detail-row">
                        <span class="detail-lbl">Amount:</span>
                        <span class="detail-val">₹${d.transaction ? d.transaction.amount : '---'}</span>
                    </div>
                    <div class="admin-detail-row">
                        <span class="detail-lbl">Bank Status:</span>
                        <span class="detail-val">${d.transaction ? d.transaction.status : '---'}</span>
                    </div>
                    <div class="admin-detail-row">
                        <span class="detail-lbl">Created:</span>
                        <span class="detail-val">${formatTime(d.created_at)}</span>
                    </div>
                    ${d.user_reason ? `<div class="admin-detail-row"><span class="detail-lbl">User Reason:</span><span class="detail-val" style="color:var(--warning);">${d.user_reason}</span></div>` : ''}
                </div>
                ${(d.audit_logs && d.audit_logs.length > 0) ? `
                    <div class="admin-audit-trail" style="padding:12px 16px;border-top:1px solid var(--border-light);">
                        <div style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:var(--text-muted);margin-bottom:8px;">AI Audit Trail</div>
                        ${d.audit_logs.map(log => `
                            <div style="font-size:12px;color:var(--text-secondary);padding:4px 0;border-bottom:1px solid var(--border-light);">
                                <span style="color:var(--text-muted);">${formatTime(log.timestamp)}</span> — ${log.state_change}
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                ${actionHtml}
            </div>
        `;
    }).join("");
}

async function refreshTransactions() {
    try {
        const txns = await fetchAdminTransactions();
        renderAdminTransactions(txns);
    } catch (err) {
        toast("Failed to load transactions", "error");
    }
}

function renderAdminTransactions(transactions) {
    const list = document.getElementById("admin-transactions-list");
    const empty = document.getElementById("admin-empty-transactions");

    if (!transactions || transactions.length === 0) {
        list.classList.add("hidden");
        empty.classList.remove("hidden");
        return;
    }

    list.classList.remove("hidden");
    empty.classList.add("hidden");

    list.innerHTML = transactions.map(t => {
        const statuses = ["SUCCESS", "PENDING", "DEBITED", "FAILED", "REFUNDED"];
        const statusOptions = statuses.map(s =>
            `<option value="${s}" ${s === t.status ? "selected" : ""}>${s}</option>`
        ).join("");

        return `
            <div class="admin-dispute-card" id="admin-txn-${t.txn_id}">
                <div class="admin-card-header">
                    <div>
                        <div class="dispute-id">TXN: ${t.txn_id}</div>
                        <div class="dispute-txn">Merchant: ${t.merchant_id}</div>
                    </div>
                    <div class="admin-status-badge ${t.status.toLowerCase()}">${t.status}</div>
                </div>
                <div class="admin-card-body">
                    <div class="admin-detail-row">
                        <span class="detail-lbl">User:</span>
                        <span class="detail-val">${t.user ? t.user.name : 'Unknown'} (${t.user ? '₹' + t.user.balance.toFixed(2) : ''})</span>
                    </div>
                    <div class="admin-detail-row">
                        <span class="detail-lbl">Amount:</span>
                        <span class="detail-val">₹${t.amount}</span>
                    </div>
                    <div class="admin-detail-row">
                        <span class="detail-lbl">Created:</span>
                        <span class="detail-val">${formatTime(t.timestamp)}</span>
                    </div>
                </div>
                <div class="admin-actions flex-between" style="gap: 12px;">
                    <select class="txn-status-select" data-id="${t.txn_id}" style="flex: 1; padding: 10px; border-radius: 8px; border: 1px solid var(--border-light); background: var(--bg-level-1); color: var(--text-primary);">
                        ${statusOptions}
                    </select>
                    <button class="btn-resolve-approve btn-update-txn" data-id="${t.txn_id}" style="flex: 1;">Update Status</button>
                </div>
            </div>
        `;
    }).join("");
}

// ═══════════════════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {

    document.getElementById("view-admin").addEventListener("click", async e => {
        // Handle Approve
        if (e.target.classList.contains("btn-resolve-approve")) {
            const id = e.target.dataset.id;
            const btn = e.target;
            const reasonEl = document.getElementById(`admin-reason-${id}`);
            const reason = reasonEl ? reasonEl.value.trim() : "";
            btn.textContent = "Processing...";
            btn.disabled = true;

            try {
                const res = await adminResolve(id, "APPROVE_REFUND", reason);
                if (res.success) {
                    toast(`Refund Approved. User new balance: ₹${res.new_balance}`, "success");
                    refreshAdmin();
                } else {
                    toast(res.error || "Failed to resolve", "error");
                    btn.textContent = "✓ Approve Refund";
                    btn.disabled = false;
                }
            } catch (err) {
                toast("Network Error", "error");
            }
        }

        // Handle Reject
        if (e.target.classList.contains("btn-resolve-reject")) {
            const id = e.target.dataset.id;
            const btn = e.target;
            const reasonEl = document.getElementById(`admin-reason-${id}`);
            const reason = reasonEl ? reasonEl.value.trim() : "";
            btn.textContent = "Processing...";
            btn.disabled = true;

            try {
                const res = await adminResolve(id, "REJECT", reason);
                if (res.success) {
                    toast("Dispute Rejected", "success");
                    refreshAdmin();
                } else {
                    toast(res.error || "Failed to resolve", "error");
                    btn.textContent = "✕ Reject";
                    btn.disabled = false;
                }
            } catch (err) {
                toast("Network Error", "error");
            }
        }
    });

    // Handle Transaction Update
    document.getElementById("view-admin").addEventListener("click", async documentE => {
        if (documentE.target.classList.contains("btn-update-txn")) {
            const btn = documentE.target;
            const txnId = btn.dataset.id;
            const selectEl = document.querySelector(`.txn-status-select[data-id="${txnId}"]`);
            const newStatus = selectEl.value;

            btn.textContent = "Updating...";
            btn.disabled = true;

            try {
                const res = await adminUpdateTransactionStatus(txnId, newStatus);
                if (res.success) {
                    toast(res.message, "success");
                    refreshTransactions(); // re-render list
                } else {
                    toast(res.error || "Failed to update transaction", "error");
                }
            } catch (err) {
                toast("Network Error", "error");
            } finally {
                btn.textContent = "Update Status";
                btn.disabled = false;
            }
        }
    });

    // Reset DB Button
    document.getElementById("btn-reset-db").addEventListener("click", async () => {
        if (!confirm("Are you sure? This will delete all transactions and disputes and reset the balance to ₹25,000.")) return;

        try {
            const res = await adminReset();
            if (res.success) {
                toast("Database Reset Successful", "success");
                refreshAdmin();
                refreshTransactions();
            }
        } catch (err) {
            toast("Failed to reset database", "error");
        }
    });

    // Tab Navigation
    document.getElementById("admin-tabs").addEventListener("click", e => {
        const chip = e.target.closest(".filter-chip");
        if (!chip) return;

        // Update active class on chips
        document.querySelectorAll("#admin-tabs .filter-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");

        // Hide all tabs
        document.querySelectorAll(".admin-tab-content").forEach(c => c.classList.add("hidden"));
        document.querySelectorAll(".admin-tab-content").forEach(c => c.classList.remove("active"));

        // Show selected tab
        const tabId = chip.dataset.tab;
        const activeTab = document.getElementById(`tab-${tabId}`);
        activeTab.classList.remove("hidden");
        activeTab.classList.add("active");

        // Refresh data based on tab
        if (tabId === "disputes") refreshAdmin();
        if (tabId === "transactions") refreshTransactions();
    });

    // Initial load
    refreshAdmin();
});
