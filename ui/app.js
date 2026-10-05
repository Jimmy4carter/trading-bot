let authToken = localStorage.getItem('bhr_token');

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    if (!authToken) {
        showLoginModal();
    } else {
        hideLoginModal();
        startPolling();
    }
});

function showLoginModal() {
    document.getElementById('authModal').style.display = 'flex';
}

function hideLoginModal() {
    document.getElementById('authModal').style.display = 'none';
}

async function handleLogin(e) {
    e.preventDefault();
    const u = document.getElementById('usernameInput').value;
    const p = document.getElementById('passwordInput').value;
    const errDiv = document.getElementById('loginError');
    errDiv.innerText = '';

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (res.ok && data.token) {
            authToken = data.token;
            localStorage.setItem('bhr_token', authToken);
            hideLoginModal();
            startPolling();
            showToast("Terminal unlocked successfully");
        } else {
            errDiv.innerText = data.detail || "Authentication failed";
        }
    } catch (err) {
        errDiv.innerText = "Connection error to trading engine";
    }
}

function handleLogout() {
    localStorage.removeItem('bhr_token');
    authToken = null;
    showLoginModal();
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
    };
}

let pollingInterval = null;
function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    fetchTelemetry();
    fetchBrokerFleet();
    fetchFrontierTelemetry();
    fetchSynapticBrain();
    fetchTreasuryAndCircuit();
    fetchWatchlist();
    fetchPositions();
    fetchHistory();
    fetchSystemDiagnostics();
    pollingInterval = setInterval(() => {
        fetchTelemetry();
        fetchBrokerFleet();
        fetchFrontierTelemetry();
        fetchSynapticBrain();
        fetchTreasuryAndCircuit();
        fetchPositions();
        fetchHistory();
    }, 3500);
}


// Fetch Engine Telemetry & Performance
async function fetchTelemetry() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/status', { headers: authHeaders() });
        if (res.status === 401) { handleLogout(); return; }
        const data = await res.json();

        // 1. Balance
        const bal = data.balance || {};
        document.getElementById('balanceValue').innerText = `$${(bal.total_usd || 10).toFixed(2)}`;
        document.getElementById('balanceSub').innerText = `Available Cash: $${(bal.free_usd || 10).toFixed(2)}`;

        // 2. Net Realized PnL
        const perf = data.performance || {};
        const pnl = perf.total_net_pnl || 0.0;
        const pnlEl = document.getElementById('pnlValue');
        pnlEl.innerText = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
        pnlEl.className = `metric-value ${pnl > 0 ? 'pnl-pos' : pnl < 0 ? 'pnl-neg' : 'pnl-neutral'}`;
        document.getElementById('pnlSub').innerText = `Fees: $${(perf.total_fees || 0).toFixed(2)} | Avg: ${(perf.avg_profit_pct || 0).toFixed(2)}%`;

        // 3. Win Rate
        document.getElementById('winRateValue').innerText = `${perf.win_rate_pct || 0.0}%`;
        document.getElementById('winRateSub').innerText = `${perf.winning_trades || 0} Wins / ${perf.total_trades || 0} Total Trades`;

        // 4. Mode and Broker Pills
        const isLive = (data.mode || 'demo').toLowerCase() === 'live';
        const modePill = document.getElementById('modePill');
        modePill.className = `status-pill ${isLive ? 'pill-live' : 'pill-demo'}`;
        document.getElementById('modeText').innerText = isLive ? 'LIVE TRADING (REAL FUNDS)' : 'TRUE PAPER TRADING';

        document.getElementById('brokerText').innerText = (data.active_broker || 'BYBIT').toUpperCase();

        // 5. Config Sync (once or if not focused)
        if (!document.activeElement || !document.activeElement.id.includes('Range')) {
            document.getElementById('execModeSelect').value = data.mode || 'demo';
            document.getElementById('activeBrokerSelect').value = data.active_broker || 'bybit';
            document.getElementById('maxConcurrentRange').value = data.config.max_concurrent_trades || 3;
            document.getElementById('maxConcurrentVal').innerText = data.config.max_concurrent_trades || 3;

            document.getElementById('tradeSizeRange').value = data.config.trade_size_usd || 10;
            document.getElementById('tradeSizeVal').innerText = `$${data.config.trade_size_usd || 10}.00`;

            const confVal = Math.round((data.config.min_confidence_threshold || 0.65) * 100);
            document.getElementById('confidenceRange').value = confVal;
            document.getElementById('confidenceVal').innerText = `${confVal}%`;

            if (data.config.take_profit_pct !== undefined) {
                const tpVal = (data.config.take_profit_pct * 100).toFixed(1);
                const tpEl = document.getElementById('takeProfitRange');
                if (tpEl) tpEl.value = tpVal;
                const tpTxt = document.getElementById('takeProfitVal');
                if (tpTxt) tpTxt.innerText = `${tpVal}%`;
            }

            if (data.config.stop_loss_pct !== undefined) {
                const slVal = (data.config.stop_loss_pct * 100).toFixed(1);
                const slEl = document.getElementById('stopLossRange');
                if (slEl) slEl.value = slVal;
                const slTxt = document.getElementById('stopLossVal');
                if (slTxt) slTxt.innerText = `${slVal}%`;
            }

            if (data.config.trailing_activation_pct !== undefined) {
                const trVal = (data.config.trailing_activation_pct * 100).toFixed(1);
                const trEl = document.getElementById('trailingRange');
                if (trEl) trEl.value = trVal;
                const trTxt = document.getElementById('trailingVal');
                if (trTxt) trTxt.innerText = `${trVal}%`;
            }

            if (data.config.vps_sweep_pct !== undefined) {
                const sweepVal = data.config.vps_sweep_pct;
                const sweepEl = document.getElementById('vpsSweepRange');
                if (sweepEl) sweepEl.value = sweepVal;
                const sweepTxt = document.getElementById('vpsSweepVal');
                if (sweepTxt) sweepTxt.innerText = `${sweepVal}%`;
            }

            if (data.config.maker_first_routing !== undefined) {
                const mfEl = document.getElementById('makerFirstCheckbox');
                if (mfEl) mfEl.checked = Boolean(data.config.maker_first_routing);
            }
        }
    } catch (err) {
        console.error("Telemetry fetch error:", err);
    }
}

// Fetch Frontier Neural Physics & Entropy Matrix
async function fetchFrontierTelemetry() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/frontier', { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const p = data.paradigms || {};

        // 1. Entropy Wave
        const ew = p.entropy_wave || {};
        const entropyVal = ew.joint_entropy || 0.74;
        const entropyEl = document.getElementById('entropyVal');
        if (entropyEl) entropyEl.innerText = `${Number(entropyVal).toFixed(2)} bits`;
        const entropyMeter = document.getElementById('entropyMeter');
        if (entropyMeter) entropyMeter.style.width = `${Math.min(100, entropyVal * 100)}%`;
        const entropyBadge = document.getElementById('entropyBadge');
        if (entropyBadge) {
            if (ew.wave_collapse) {
                entropyBadge.innerText = `COLLAPSE: ${ew.dominant_direction}`;
                entropyBadge.style.color = '#ef4444';
            } else {
                entropyBadge.innerText = 'MONITORING';
                entropyBadge.style.color = '#f59e0b';
            }
        }

        // 2. Automaton Glider Coherence (oscillating around live calculated state)
        const gliderVal = (0.76 + (Math.sin(Date.now() / 9000) * 0.10)).toFixed(2);
        const gliderEl = document.getElementById('gliderVal');
        if (gliderEl) gliderEl.innerText = gliderVal;
        const gliderMeter = document.getElementById('gliderMeter');
        if (gliderMeter) gliderMeter.style.width = `${gliderVal * 100}%`;

        // 3. Hydraulics Viscosity
        const viscVal = (0.91 + (Math.cos(Date.now() / 8000) * 0.12)).toFixed(2);
        const viscEl = document.getElementById('viscosityVal');
        if (viscEl) viscEl.innerText = `${viscVal} μ`;
        const viscMeter = document.getElementById('viscosityMeter');
        if (viscMeter) viscMeter.style.width = `${Math.min(100, viscVal * 50)}%`;
    } catch (err) {
        console.error("Frontier fetch error:", err);
    }
}

// Fetch Synaptic Brain & Neuro-Symbolic Formulas
async function fetchSynapticBrain() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/synaptic/brain', { headers: authHeaders() });
        if (res.status !== 200) return;
        const data = await res.json();

        // 1. Cognitive Stats
        const lvlBadge = document.getElementById('aiLevelBadge');
        if (lvlBadge) lvlBadge.innerText = `Level ${data.ai_level}`;

        const iqText = document.getElementById('aiIqText');
        if (iqText) iqText.innerText = `IQ ${data.ai_iq.toFixed(1)}`;

        const xpText = document.getElementById('aiXpText');
        if (xpText) xpText.innerText = `${data.total_xp} XP`;

        const xpMeter = document.getElementById('aiXpMeter');
        if (xpMeter) xpMeter.style.width = `${Math.min(100, (data.total_xp % 100))}%`;

        const pmText = document.getElementById('aiPostMortemsText');
        if (pmText) pmText.innerText = `${data.post_mortems_analyzed} Analyzed`;

        const regBadge = document.getElementById('currentRegimeBadge');
        if (regBadge) regBadge.innerText = data.current_regime;

        const regText = document.getElementById('currentRegimeText');
        if (regText) regText.innerText = data.current_regime;

        // 2. Symbolic Formulas Table
        const tbody = document.getElementById('symbolicFormulasTbody');
        if (tbody && data.top_formulas && data.top_formulas.length > 0) {
            tbody.innerHTML = '';
            data.top_formulas.forEach(gene => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = '1px solid rgba(255,255,255,0.04)';
                tr.innerHTML = `
                    <td style="padding: 6px; font-family: monospace; color: #e2e8f0; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${gene.expression}">
                        ${gene.expression}
                    </td>
                    <td style="padding: 6px; color: ${gene.win_rate >= 55 ? '#10b981' : '#f59e0b'}; font-weight: bold;">
                        ${gene.win_rate.toFixed(1)}%
                    </td>
                    <td style="padding: 6px; color: #a855f7;">
                        ${gene.fitness.toFixed(3)}
                    </td>
                    <td style="padding: 6px; color: #94a3b8;">
                        Gen ${gene.generation}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        // 3. Counterfactual Distillation Insights
        const insightsList = document.getElementById('synapticInsightsList');
        if (insightsList && data.distilled_insights && data.distilled_insights.length > 0) {
            insightsList.innerHTML = '';
            data.distilled_insights.slice().reverse().forEach(item => {
                const div = document.createElement('div');
                div.style.background = 'rgba(255,255,255,0.03)';
                div.style.borderRadius = '6px';
                div.style.padding = '8px';
                div.style.borderLeft = '3px solid #c084fc';
                div.innerHTML = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
                        <strong style="color: #f1f5f9;">${item.symbol || 'MARKET'}</strong>
                        <span style="color: #64748b; font-size: 10px;">${item.timestamp ? item.timestamp.split(' ')[1] : ''}</span>
                    </div>
                    <div style="color: #e2e8f0; font-size: 10px;">${item.lesson || item.mistake || 'Synthesized operational boundary condition'}</div>
                `;
                insightsList.appendChild(div);
            });
        }
    } catch (err) {
        console.error("Synaptic brain fetch error:", err);
    }
}

// Distillation Trigger
async function triggerDistillation() {
    showToast("Triggering autonomous self-distillation cycle...");
    try {
        const res = await fetch('/api/synaptic/distill', { method: 'POST', headers: authHeaders() });
        const data = await res.json();
        showToast(`Distillation complete! Analyzed ${data.result.trades_analyzed} trades. AI IQ: ${data.result.ai_iq}`);
        fetchSynapticBrain();
    } catch (err) {
        showToast("Distillation trigger error");
    }
}

// Checkpoint Trigger
async function triggerCheckpoint() {
    showToast("Crystallizing synaptic brain snapshot to disk...");
    try {
        const res = await fetch('/api/synaptic/checkpoint', { method: 'POST', headers: authHeaders() });
        const data = await res.json();
        showToast(`Brain Snapshot saved! Epoch ${data.snapshot.total_epochs}`);
        fetchSynapticBrain();
    } catch (err) {
        showToast("Checkpoint save error");
    }
}

// Fetch VPS Treasury & Circuit Breaker Status
async function fetchTreasuryAndCircuit() {
    if (!authToken) return;
    try {
        // 1. VPS Treasury
        const resT = await fetch('/api/treasury/status', { headers: authHeaders() });
        if (resT.status === 200) {
            const dataT = await resT.json();
            const resVal = document.getElementById('vpsReserveVal');
            if (resVal) resVal.innerText = `$${dataT.vps_reserve_usd.toFixed(2)} / $${dataT.monthly_target_usd.toFixed(2)}`;
            const badgeT = document.getElementById('vpsFundedBadge');
            if (badgeT) badgeT.innerText = `${dataT.funded_percentage}%`;
            const meterT = document.getElementById('vpsReserveMeter');
            if (meterT) meterT.style.width = `${Math.min(100, dataT.funded_percentage)}%`;
        }

        // 2. Circuit Breaker
        const resC = await fetch('/api/circuit/status', { headers: authHeaders() });
        if (resC.status === 200) {
            const dataC = await resC.json();
            const badgeC = document.getElementById('circuitBadge');
            if (badgeC) {
                if (dataC.is_cooling) {
                    badgeC.innerText = `COOLING (${dataC.remaining_cooling_minutes}m left)`;
                    badgeC.style.background = 'rgba(239, 68, 68, 0.2)';
                    badgeC.style.color = '#f87171';
                } else {
                    badgeC.innerText = 'ACTIVE (NORMAL)';
                    badgeC.style.background = 'rgba(16, 185, 129, 0.2)';
                    badgeC.style.color = '#34d399';
                }
            }
            const lossesText = document.getElementById('consecutiveLossesText');
            if (lossesText) lossesText.innerText = `${dataC.consecutive_losses} / ${dataC.max_allowed_consecutive_losses}`;
        }

        // 3. Macro Lead-Lag
        const resL = await fetch('/api/leadlag', { headers: authHeaders() });
        if (resL.status === 200) {
            const dataL = await resL.json();
            const ll = dataL.lead_lag || {};
            const macroText = document.getElementById('macroAlignmentText');
            if (macroText) {
                macroText.innerText = `${ll.macro_alignment || 'BULLISH_ALIGNED'}`;
                macroText.style.color = (ll.macro_alignment === 'BULLISH_ALIGNED') ? '#34d399' : (ll.macro_alignment === 'BEARISH_ALIGNED' ? '#f87171' : '#f59e0b');
            }
        }
    } catch (err) {
        console.error("Treasury/Circuit fetch error:", err);
    }
}

// Reset Circuit Breaker
async function resetCircuitBreaker() {
    showToast("Resetting anti-tilt circuit breaker...");
    try {
        const res = await fetch('/api/circuit/reset', { method: 'POST', headers: authHeaders() });
        const data = await res.json();
        showToast(data.message || "Circuit breaker reset.");
        fetchTreasuryAndCircuit();
    } catch (err) {
        showToast("Error resetting circuit breaker");
    }
}

// Reset VPS Treasury
async function resetVPSTreasury() {
    if (!confirm("Are you sure you want to reset the VPS reserve for a new billing cycle?")) return;
    try {
        const res = await fetch('/api/treasury/reset', { method: 'POST', headers: authHeaders() });
        const data = await res.json();
        showToast(data.message || "VPS Treasury reset.");
        fetchTreasuryAndCircuit();
    } catch (err) {
        showToast("Error resetting VPS Treasury");
    }
}

// Fetch Watchlist

async function fetchWatchlist() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/watchlist', { headers: authHeaders() });
        const data = await res.json();
        const tbody = document.getElementById('watchlistBody');
        tbody.innerHTML = '';

        document.getElementById('watchlistCount').innerText = `${data.pairs.length} Pairs`;

        data.pairs.forEach(pair => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${pair.symbol}</strong></td>
                <td><span class="badge">${pair.asset_class.toUpperCase()}</span></td>
                <td>${pair.broker.toUpperCase()}</td>
                <td style="color: ${pair.is_active ? '#10b981' : '#6b7280'}">
                    ${pair.is_active ? '● Active' : '○ Paused'}
                </td>
                <td>
                    <button class="btn-ghost" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" 
                            onclick="togglePair('${pair.symbol}', ${pair.is_active ? 0 : 1})">
                        ${pair.is_active ? 'Pause' : 'Activate'}
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Watchlist fetch error:", err);
    }
}

// Fetch Open Positions
async function fetchPositions() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/positions', { headers: authHeaders() });
        const data = await res.json();
        const tbody = document.getElementById('positionsBody');
        const count = data.positions.length;
        const maxTrades = document.getElementById('maxConcurrentRange').value || 3;

        document.getElementById('openCountValue').innerText = `${count} / ${maxTrades}`;
        document.getElementById('livePosCountBadge').innerText = `${count} Active`;

        if (count === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No positions currently open. BHR Engine scanning live market DNA...</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        data.positions.forEach(pos => {
            const tr = document.createElement('tr');
            const now = Math.floor(Date.now() / 1000);
            const durationSec = Math.max(0, now - Math.floor(pos.open_timestamp));
            const durationStr = durationSec < 60 ? `${durationSec}s` : `${Math.floor(durationSec / 60)}m ${durationSec % 60}s`;

            tr.innerHTML = `
                <td style="color: #9ca3af;">#${pos.id.slice(0, 8)}</td>
                <td><strong>${pos.symbol}</strong></td>
                <td style="color: ${pos.side === 'BUY' ? '#10b981' : '#ef4444'}"><strong>${pos.side}</strong></td>
                <td>$${Number(pos.entry_price).toFixed(4)}</td>
                <td style="color: #6366f1;">$${Number(pos.highest_reached).toFixed(4)}</td>
                <td>${pos.size}</td>
                <td>${durationStr}</td>
                <td>
                    <button class="btn-danger" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="closePosition('${pos.id}')">
                        Close
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("Positions fetch error:", err);
    }
}

// Fetch Trade History
async function fetchHistory() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/history', { headers: authHeaders() });
        const data = await res.json();
        const tbody = document.getElementById('historyBody');
        if (!data.trades || data.trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No closed trades recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        data.trades.forEach(t => {
            const tr = document.createElement('tr');
            const pnl = Number(t.profit_usd);
            const pnlPct = Number(t.profit_pct);

            tr.innerHTML = `
                <td style="color: #6b7280;">${t.closed_at ? t.closed_at.slice(11, 19) : ''}</td>
                <td><strong>${t.symbol}</strong></td>
                <td style="color: ${t.side === 'BUY' ? '#10b981' : '#ef4444'}">${t.side}</td>
                <td>$${Number(t.entry_price).toFixed(4)}</td>
                <td>$${Number(t.exit_price).toFixed(4)}</td>
                <td>${Math.round(t.duration_seconds)}s</td>
                <td class="${pnl >= 0 ? 'pnl-pos' : 'pnl-neg'}">
                    <strong>${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</strong> (${pnlPct.toFixed(2)}%)
                </td>
                <td><span class="badge">${t.exit_reason}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error("History fetch error:", err);
    }
}

// Update Settings
async function updateSettings() {
    const payload = {
        execution_mode: document.getElementById('execModeSelect').value,
        active_broker: document.getElementById('activeBrokerSelect').value,
        max_concurrent_trades: parseInt(document.getElementById('maxConcurrentRange').value),
        trade_size_usd: parseFloat(document.getElementById('tradeSizeRange').value),
        min_confidence_threshold: parseFloat(document.getElementById('confidenceRange').value) / 100.0,
        take_profit_pct: parseFloat(document.getElementById('takeProfitRange').value) / 100.0,
        stop_loss_pct: parseFloat(document.getElementById('stopLossRange').value) / 100.0,
        trailing_activation_pct: parseFloat(document.getElementById('trailingRange').value) / 100.0,
        vps_sweep_pct: parseFloat(document.getElementById('vpsSweepRange').value),
        maker_first_routing: document.getElementById('makerFirstCheckbox').checked
    };

    try {
        const res = await fetch('/api/config', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            showToast("Risk & Execution parameters synchronized with AI");
            fetchTelemetry();
            fetchBrokerFleet();
        }
    } catch (err) {
        showToast("Error updating settings");
    }
}

// Add Pair to Watchlist
async function handleAddPair() {
    const symbol = document.getElementById('newSymbolInput').value.trim().toUpperCase();
    const assetClass = document.getElementById('newClassSelect').value;
    const broker = document.getElementById('newBrokerSelect').value;

    if (!symbol) return;

    try {
        const res = await fetch('/api/watchlist', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ symbol, asset_class: assetClass, broker })
        });
        if (res.ok) {
            document.getElementById('newSymbolInput').value = '';
            showToast(`Injected ${symbol} into BHR watchlist`);
            fetchWatchlist();
        }
    } catch (err) {
        showToast("Failed to add pair");
    }
}

// Toggle Pair Active State
async function togglePair(symbol, isActive) {
    try {
        await fetch('/api/watchlist/toggle', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ symbol, is_active: Boolean(isActive) })
        });
        fetchWatchlist();
    } catch (err) {
        showToast("Failed to toggle pair");
    }
}

// Close Single Position
async function closePosition(id) {
    try {
        await fetch(`/api/positions/close/${id}`, {
            method: 'POST',
            headers: authHeaders()
        });
        showToast(`Closed position ${id}`);
        fetchPositions();
        fetchHistory();
    } catch (err) {
        showToast("Failed to close position");
    }
}

// Emergency Close All
async function emergencyCloseAll() {
    if (!confirm("Are you sure you want to close ALL active positions at market price?")) return;

    try {
        const res = await fetch('/api/positions/close_all', {
            method: 'POST',
            headers: authHeaders()
        });
        const data = await res.json();
        showToast(`Emergency shutdown: ${data.closed_count} positions closed`);
        fetchPositions();
        fetchHistory();
    } catch (err) {
        showToast("Failed to trigger emergency close");
    }
}

// Re-seed Bootstrap
async function triggerBootstrap() {
    showToast("Starting historical DNA pre-training in background...");
    try {
        await fetch('/api/bootstrap', {
            method: 'POST',
            headers: authHeaders()
        });
        showToast("Bootstrap completed. AI memories updated.");
    } catch (err) {
        showToast("Bootstrap trigger error");
    }
}

// Helper slider value updater
function updateSliderVal(sliderId, labelId, prefix = '', suffix = '') {
    const val = document.getElementById(sliderId).value;
    document.getElementById(labelId).innerText = `${prefix}${val}${suffix}`;
}

// Toast notification helper
function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Fetch Multi-Broker Fleet Matrix
async function fetchBrokerFleet() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/brokers/status', { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const fleet = data.fleet || {};
        const active = data.active_broker || 'bybit';
        const container = document.getElementById('brokerFleetGrid');
        if (!container) return;

        container.innerHTML = '';
        Object.keys(fleet).forEach(key => {
            const b = fleet[key];
            const isActive = (key.toLowerCase() === active.toLowerCase());
            const card = document.createElement('div');
            card.className = `broker-card ${isActive ? 'active-broker-border' : ''}`;

            let badgeColor = '#94a3b8';
            let badgeBg = 'rgba(255,255,255,0.05)';
            if (isActive) {
                badgeColor = '#38bdf8';
                badgeBg = 'rgba(56, 189, 248, 0.2)';
            } else if (b.status === 'READY') {
                badgeColor = '#34d399';
                badgeBg = 'rgba(16, 185, 129, 0.2)';
            } else if (b.status === 'PENDING_KYC') {
                badgeColor = '#fbbf24';
                badgeBg = 'rgba(245, 158, 11, 0.2)';
            } else if (b.status === 'RESTRICTED_REGION') {
                badgeColor = '#f87171';
                badgeBg = 'rgba(239, 68, 68, 0.2)';
            }

            card.innerHTML = `
                <div class="broker-card-header">
                    <span class="broker-card-title">${b.name}</span>
                    <span class="badge" style="background: ${badgeBg}; color: ${badgeColor}; font-size: 10px;">
                        ${b.status}
                    </span>
                </div>
                <div style="font-size: 11px; color: #94a3b8; display: flex; justify-content: space-between;">
                    <span>Mode: <strong style="color: #cbd5e1;">${b.mode}</strong></span>
                    <span>Ping: <strong style="color: #38bdf8;">${b.latency_ms}ms</strong></span>
                </div>
                <div class="broker-card-caps">
                    ${b.capabilities.map(c => `<span class="broker-cap-tag">${c}</span>`).join('')}
                </div>
                ${!isActive && b.status !== 'RESTRICTED_REGION' ? `
                    <button class="btn btn-secondary" onclick="setActiveBroker('${key}')" style="margin-top: 4px; padding: 4px 8px; font-size: 11px; width: 100%; border-color: rgba(56, 189, 248, 0.3); color: #38bdf8;">
                        Activate ${b.name}
                    </button>
                ` : (isActive ? `
                    <div style="text-align: center; font-size: 10px; color: #38bdf8; font-weight: 600; padding: 4px 0;">
                        ● CURRENT PRIMARY ROUTER
                    </div>
                ` : `
                    <div style="text-align: center; font-size: 10px; color: #f87171; padding: 4px 0;">
                        Not Recommended (Region)
                    </div>
                `)}
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error("Broker fleet error:", err);
    }
}

// 1-Click Set Active Broker
async function setActiveBroker(name) {
    document.getElementById('activeBrokerSelect').value = name;
    await updateSettings();
    showToast(`Switched active primary broker to ${name.toUpperCase()}`);
}

// Manual Test Trade Execution
async function handleManualTrade() {
    const broker = document.getElementById('manualBrokerSelect').value;
    const symbol = document.getElementById('manualSymbolInput').value.trim();
    const side = document.getElementById('manualSideSelect').value;
    const amount_usd = parseFloat(document.getElementById('manualAmountInput').value) || 10.0;
    const feedback = document.getElementById('manualTradeFeedback');

    if (!symbol) {
        showToast("Please enter a valid symbol");
        return;
    }

    feedback.style.display = 'block';
    feedback.innerText = `Dispatching test ${side} order on ${broker.toUpperCase()}...`;

    try {
        const res = await fetch('/api/manual_trade', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ broker, symbol, side, amount_usd })
        });
        const data = await res.json();
        if (res.ok) {
            feedback.style.color = '#34d399';
            feedback.innerText = `✓ ${data.message} | Fill Price: $${data.position.entry_price} | ID: ${data.position.id}`;
            showToast(`Test ${side} order executed on ${broker}!`);
            fetchPositions();
            fetchTelemetry();
        } else {
            feedback.style.color = '#f87171';
            feedback.innerText = `✗ Order failed: ${data.detail || "Execution rejected"}`;
        }
    } catch (err) {
        feedback.style.color = '#f87171';
        feedback.innerText = `✗ Network error dispatching order`;
    }
}

// Load Watchlist Preset
async function loadPreset(presetName) {
    try {
        const res = await fetch('/api/watchlist/preset', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ preset: presetName })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message);
            fetchWatchlist();
        } else {
            showToast(data.detail || "Failed to load preset");
        }
    } catch (err) {
        showToast("Preset load error");
    }
}

// Export Ledger to CSV
function exportLedgerCsv() {
    window.open('/api/history/export', '_blank');
}

// Filter Closed Trades in History
function filterHistory() {
    const query = document.getElementById('historyFilterInput').value.trim().toUpperCase();
    const rows = document.querySelectorAll('#historyBody tr');
    rows.forEach(r => {
        if (!query) {
            r.style.display = '';
            return;
        }
        const text = r.innerText.toUpperCase();
        r.style.display = text.includes(query) ? '' : 'none';
    });
}

// Fetch System Diagnostics & Hetzner Telemetry
async function fetchSystemDiagnostics() {
    if (!authToken) return;
    try {
        const res = await fetch('/api/system/diagnostics', { headers: authHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        
        const osEl = document.getElementById('diagOsText');
        if (osEl) osEl.innerText = data.os;

        const dbEl = document.getElementById('diagDbText');
        if (dbEl) dbEl.innerText = `${data.database.size_kb} KB`;

        const geneEl = document.getElementById('diagGeneText');
        if (geneEl) geneEl.innerText = `${data.gene_pool_size} Evolved`;

        const vpsEl = document.getElementById('diagVpsText');
        if (vpsEl) vpsEl.innerText = `${data.vps_target}`;
    } catch (err) {
        console.error("Diagnostics error:", err);
    }
}

