const I18N = window.I18N || {};
const refreshButton = document.getElementById("refresh-tests");
const testResults = document.getElementById("test-results");
const startButton = document.getElementById("start-orchestrator");
const pauseButton = document.getElementById("pause-orchestrator");
const stopButton = document.getElementById("stop-orchestrator");
const saveWatchlistButton = document.getElementById("save-watchlist");
const watchlistInput = document.getElementById("watchlist-input");
const watchlistStatus = document.getElementById("watchlist-status");
const analyzeSelectedButton = document.getElementById("analyze-selected");
const analyzeAllButton = document.getElementById("analyze-all");
const analyzeInput = document.getElementById("analyze-input");
const analyzeStatus = document.getElementById("analyze-status");
const fundingAlertsPanel = document.getElementById("funding-alerts");
const logBox = document.getElementById("log-box");
const watchlistTags = document.querySelector("#watchlist .tags");

function t(key, fallback) {
  if (Object.prototype.hasOwnProperty.call(I18N, key)) {
    return I18N[key];
  }
  return fallback ?? key;
}

function tPath(path, fallback) {
  const parts = path.split(".");
  let current = I18N;
  for (const part of parts) {
    if (!current || typeof current !== "object" || !(part in current)) {
      return fallback ?? path;
    }
    current = current[part];
  }
  return current ?? fallback ?? path;
}

function format(text, params) {
  return String(text).replace(/\{(\w+)\}/g, (_, key) => {
    return key in params ? params[key] : `{${key}}`;
  });
}

async function fetchTestCenter() {
  testResults.textContent = t("test_center_running", "Kontroller çalıştırılıyor...");
  try {
    const response = await fetch("/api/test-center/checks");
    const data = await response.json();
    if (!Array.isArray(data)) {
      testResults.textContent = t("test_center_unexpected", "Test Merkezi beklenmedik yanıt döndürdü.");
      return;
    }
    testResults.innerHTML = data
      .map(
        (check) =>
          `<div class="test-result ${check.status}">` +
          `<strong>${check.name}</strong> — ${tPath(`status_labels.${check.status}`, check.status)}<br/>` +
          `<span>${check.message}</span>` +
          (check.details && check.details.mock_mode ? `<br/><em>${t("test_center_mock", "MOCK MODU AKTİF")}</em>` : "") +
          (check.next_step ? `<br/><em>${check.next_step}</em>` : "") +
          "</div>"
      )
      .join("");
  } catch (err) {
    testResults.textContent = format(t("test_center_error", "Test Merkezi hatası: {error}"), { error: err });
  }
}

if (refreshButton) {
  refreshButton.addEventListener("click", fetchTestCenter);
}

async function updateOrchestrator(action) {
  const response = await fetch(`/api/orchestrator/${action}`, { method: "POST" });
  const data = await response.json();
  return data;
}

if (startButton) {
  startButton.addEventListener("click", async () => {
    const data = await updateOrchestrator("start");
    analyzeStatus.textContent = format(t("orchestrator_status", "Orkestratör: {status}"), {
      status: tPath(`orchestrator_statuses.${data.status}`, data.status),
    });
  });
}

if (pauseButton) {
  pauseButton.addEventListener("click", async () => {
    const data = await updateOrchestrator("pause");
    analyzeStatus.textContent = format(t("orchestrator_status", "Orkestratör: {status}"), {
      status: tPath(`orchestrator_statuses.${data.status}`, data.status),
    });
  });
}

if (stopButton) {
  stopButton.addEventListener("click", async () => {
    const data = await updateOrchestrator("stop");
    analyzeStatus.textContent = format(t("orchestrator_status", "Orkestratör: {status}"), {
      status: tPath(`orchestrator_statuses.${data.status}`, data.status),
    });
  });
}

if (saveWatchlistButton) {
  saveWatchlistButton.addEventListener("click", async () => {
    const payload = { symbols: watchlistInput.value };
    const response = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    watchlistStatus.textContent = data.error
      ? format(t("watchlist_error", "Hata: {error}"), { error: data.error })
      : format(t("watchlist_saved", "{count} sembol kaydedildi."), { count: data.symbols.length });
    if (!data.error) {
      renderWatchlistTags(data.symbols);
    }
  });
}

if (analyzeSelectedButton) {
  analyzeSelectedButton.addEventListener("click", async () => {
    const symbols = analyzeInput.value.replace(/,/g, " ").split(/\s+/).filter(Boolean);
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols }),
    });
    const data = await response.json();
    analyzeStatus.textContent = data.error
      ? format(t("analyze_error", "Analiz hatası: {error}"), { error: data.error })
      : data.message || format(t("analyze_processed", "{count} sembol işlendi."), { count: data.processed });
  });
}

if (analyzeAllButton) {
  analyzeAllButton.addEventListener("click", async () => {
    const response = await fetch("/api/analyze/all", { method: "POST" });
    const data = await response.json();
    analyzeStatus.textContent = data.error
      ? format(t("analyze_error", "Analiz hatası: {error}"), { error: data.error })
      : data.message || format(t("analyze_processed", "{count} sembol işlendi."), { count: data.processed });
  });
}

async function refreshFundingAlerts() {
  if (!fundingAlertsPanel) return;
  const response = await fetch("/api/funding-alerts");
  const data = await response.json();
  if (!Array.isArray(data) || data.length === 0) {
    fundingAlertsPanel.innerHTML = `<div class="alert">${t("funding_none", "Aktif fonlama uyarısı yok.")}</div>`;
    return;
  }
  fundingAlertsPanel.innerHTML = data
    .map(
      (alert) =>
        `<div class="stacked-item">` +
        `<strong>${alert.symbol}</strong> — ${format(t("funding_missing", "Eksik nakit: {amount}"), {
          amount: Number(alert.missing_cash).toFixed(2),
        })}<br/>` +
        `<span>${format(t("funding_actions", "Aksiyonlar: {actions}"), { actions: alert.proposed_actions })}</span><br/>` +
        `<span>${alert.created_at}</span>` +
        `</div>`
    )
    .join("");
}

async function refreshLogs() {
  if (!logBox) return;
  const response = await fetch("/api/logs?limit=50");
  const data = await response.json();
  if (!Array.isArray(data) || data.length === 0) {
    logBox.textContent = t("logs_empty", "Henüz log yok.");
    return;
  }
  logBox.innerHTML = data
    .map((row) => `<div>[${row.created_at}] ${row.level.toUpperCase()}: ${row.message}</div>`)
    .join("");
}

refreshFundingAlerts();
refreshLogs();
fetch("/api/watchlist").then((response) => response.json()).then((data) => {
  if (data.symbols) {
    renderWatchlistTags(data.symbols);
  }
});
setInterval(refreshFundingAlerts, 15000);
setInterval(refreshLogs, 15000);

function renderWatchlistTags(symbols) {
  if (!watchlistTags) return;
  watchlistTags.innerHTML = symbols.map((symbol) => `<span>${symbol}</span>`).join("");
}
