// static/js/offline.js

// ==================== SALES ====================

function savePendingSale(saleData) {
    let pending = JSON.parse(localStorage.getItem('pendingSales') || '[]');
    pending.push({
        id: Date.now() + '_' + Math.random().toString(36).substr(2, 5),
        data: saleData,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('pendingSales', JSON.stringify(pending));
    updatePendingBadge();
}

function getPendingSales() {
    return JSON.parse(localStorage.getItem('pendingSales') || '[]');
}

function removePendingSale(localId) {
    let pending = getPendingSales();
    pending = pending.filter(s => s.id !== localId);
    localStorage.setItem('pendingSales', JSON.stringify(pending));
    updatePendingBadge();
}

async function syncPendingSales() {
    const pending = getPendingSales();
    if (pending.length === 0) return;

    let synced = 0;
    for (const sale of pending) {
        try {
            const response = await fetch('/api/sales/complete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(sale.data)
            });
            if (response.ok) {
                removePendingSale(sale.id);
                synced++;
            } else {
                console.warn(`Failed to sync sale ${sale.id} – status: ${response.status}`);
            }
        } catch (err) {
            console.warn(`Sync error for sale ${sale.id}:`, err);
            break; // stop if network fails
        }
    }
    if (synced > 0) {
        console.log(`✅ ${synced} offline sale(s) synced.`);
    }
    updatePendingBadge();
}

// ==================== PURCHASES ====================

function savePendingPurchase(payload, actionType, batchId = null) {
    let pending = JSON.parse(localStorage.getItem('pendingPurchases') || '[]');
    pending.push({
        id: Date.now() + '_' + Math.random().toString(36).substr(2, 5),
        type: actionType,        // 'add' or 'update'
        batchId: batchId,        // only for updates
        data: payload,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem('pendingPurchases', JSON.stringify(pending));
    updatePendingBadge();
}

function getPendingPurchases() {
    return JSON.parse(localStorage.getItem('pendingPurchases') || '[]');
}

function removePendingPurchase(localId) {
    let pending = getPendingPurchases();
    pending = pending.filter(p => p.id !== localId);
    localStorage.setItem('pendingPurchases', JSON.stringify(pending));
    updatePendingBadge();
}

async function syncPendingPurchases() {
    const pending = getPendingPurchases();
    if (pending.length === 0) return;

    let synced = 0;
    for (const entry of pending) {
        try {
            let url = '/api/purchases';
            let method = 'POST';
            if (entry.type === 'update' && entry.batchId) {
                url = `/api/purchases/${entry.batchId}`;
                method = 'PUT';
            }
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(entry.data)
            });
            if (response.ok) {
                removePendingPurchase(entry.id);
                synced++;
            } else {
                console.warn(`Failed to sync purchase ${entry.id} – status: ${response.status}`);
            }
        } catch (err) {
            console.warn(`Sync error for purchase ${entry.id}:`, err);
            break; // stop if network fails
        }
    }
    if (synced > 0) {
        console.log(`✅ ${synced} offline purchase(s) synced.`);
    }
    updatePendingBadge();
}

// ==================== BADGE (unified) ====================

function updatePendingBadge() {
    const salesCount = getPendingSales().length;
    const purchasesCount = getPendingPurchases().length;
    const total = salesCount + purchasesCount;

    const badge = document.getElementById('pending-badge');
    if (badge) {
        if (total > 0) {
            badge.textContent = `${total} pending`;
            badge.style.display = 'inline';
            badge.title = `${salesCount} sale(s), ${purchasesCount} purchase(s) pending sync`;
        } else {
            badge.textContent = '';
            badge.style.display = 'none';
        }
    }
}

// ==================== AUTO-SYNC ON RECONNECT ====================

window.addEventListener('online', function() {
    console.log('🌐 Connection restored – syncing pending items...');
    syncPendingSales();
    syncPendingPurchases();
});

// ==================== BADGE UPDATE ON PAGE LOAD ====================

document.addEventListener('DOMContentLoaded', function() {
    updatePendingBadge();
});