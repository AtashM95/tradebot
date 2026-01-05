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
const liveUnlockCheckbox = document.getElementById("live-unlock-checkbox");
const liveUnlockPin = document.getElementById("live-unlock-pin");
const liveUnlockPhrase = document.getElementById("live-unlock-phrase");
const liveUnlockButton = document.getElementById("live-unlock-button");
const liveUnlockStatus = document.getElementById("live-unlock-status");

function t(key, fallback = "") {
  return I18N[key] ?? fallback ?? key;
}

function tPath(path, fallback = "") {
  return path.split(".").reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : null), I18N) ?? fallback;
}

function format(template, params = {}) {
  return template.replace(/\{(\w+)\}/g, (match, key) => (params[key] !== undefined ? params[key] : match));
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
    const statusLabel = tPath(`orchestrator_statuses.${data.status}`, data.status);
    analyzeStatus.textContent = format(t("orchestrator_status", "Orkestratör: {status}"), { status: statusLabel });
  });
}

if (pauseButton) {
  pauseButton.addEventListener("click", async () => {
    const data = await updateOrchestrator("pause");
    const statusLabel = tPath(`orchestrator_statuses.${data.status}`, data.status);
    analyzeStatus.textContent = format(t("orchestrator_status", "Orkestratör: {status}"), { status: statusLabel });
  });
}

if (stopButton) {
  stopButton.addEventListener("click", async () => {
    const data = await updateOrchestrator("stop");
    const statusLabel = tPath(`orchestrator_statuses.${data.status}`, data.status);
    analyzeStatus.textContent = format(t("orchestrator_status", "Orkestratör: {status}"), { status: statusLabel });
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
    if (data.error) {
      analyzeStatus.textContent = format(t("analyze_error", "Analiz hatası: {error}"), { error: data.error });
      return;
    }
    analyzeStatus.textContent = data.message || format(t("analyze_processed", "{count} sembol işlendi."), { count: data.processed });
  });
}

if (analyzeAllButton) {
  analyzeAllButton.addEventListener("click", async () => {
    const response = await fetch("/api/analyze/all", { method: "POST" });
    const data = await response.json();
    if (data.error) {
      analyzeStatus.textContent = format(t("analyze_error", "Analiz hatası: {error}"), { error: data.error });
      return;
    }
    analyzeStatus.textContent = data.message || format(t("analyze_processed", "{count} sembol işlendi."), { count: data.processed });
  });
}

if (liveUnlockButton) {
  liveUnlockButton.addEventListener("click", async () => {
    const payload = {
      live_checkbox: !!liveUnlockCheckbox?.checked,
      pin: liveUnlockPin?.value || "",
      phrase: liveUnlockPhrase?.value || "",
    };
    const response = await fetch("/api/live/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (data.error) {
      liveUnlockStatus.textContent = format(t("live_unlock_error", "Canlı kilit açılamadı: {error}"), {
        error: data.error,
      });
      return;
    }
    liveUnlockStatus.textContent = format(t("live_unlock_success", "Canlı oturum açıldı. Geçerlilik: {expires}"), {
      expires: data.expires_at,
    });
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
        `<strong>${alert.symbol}</strong> — ${format(t("funding_missing", "Eksik nakit: ${amount}"), { amount: alert.missing_cash })}<br/>` +
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
    .map((row) => {
      const levelLabel = tPath(`log_levels.${row.level}`, row.level.toUpperCase());
      return `<div>[${row.created_at}] ${levelLabel}: ${row.message}</div>`;
    })
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
