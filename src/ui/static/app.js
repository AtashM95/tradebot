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
const backtestRunButton = document.getElementById("backtest-run");
const backtestSymbolsInput = document.getElementById("backtest-symbols");
const backtestYearsInput = document.getElementById("backtest-years");
const backtestTrainInput = document.getElementById("backtest-train-days");
const backtestTestInput = document.getElementById("backtest-test-days");
const backtestStepInput = document.getElementById("backtest-step-days");
const backtestResults = document.getElementById("backtest-results");
const modelListButton = document.getElementById("model-list");
const modelActiveButton = document.getElementById("model-active");
const modelSetButton = document.getElementById("model-set-active");
const modelIdInput = document.getElementById("model-id");
const modelDriftBaseline = document.getElementById("model-drift-baseline");
const modelDriftCurrent = document.getElementById("model-drift-current");
const modelDriftButton = document.getElementById("model-drift-check");
const modelShadowFeatures = document.getElementById("model-shadow-features");
const modelShadowTarget = document.getElementById("model-shadow-target");
const modelShadowCandidate = document.getElementById("model-shadow-candidate");
const modelShadowActive = document.getElementById("model-shadow-active");
const modelShadowButton = document.getElementById("model-shadow-test");
const modelCenterResults = document.getElementById("model-center-results");
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

if (backtestRunButton) {
  backtestRunButton.addEventListener("click", async () => {
    if (!backtestResults) return;
    backtestResults.textContent = t("backtest_running", "Geri test çalışıyor...");
    const symbols = backtestSymbolsInput?.value?.trim();
    const payload = {
      symbols: symbols || undefined,
      years: Number(backtestYearsInput?.value || 5),
      train_days: Number(backtestTrainInput?.value || 504),
      test_days: Number(backtestTestInput?.value || 126),
      step_days: Number(backtestStepInput?.value || 63),
    };
    try {
      const response = await fetch("/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) {
        backtestResults.textContent = format(t("backtest_error", "Geri test hatası: {error}"), {
          error: data.detail || "unknown",
        });
        return;
      }
      backtestResults.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      backtestResults.textContent = format(t("backtest_error", "Geri test hatası: {error}"), { error: err });
    }
  });
}

function renderModelResult(data) {
  if (!modelCenterResults) return;
  modelCenterResults.textContent = JSON.stringify(data, null, 2);
}

if (modelListButton) {
  modelListButton.addEventListener("click", async () => {
    const response = await fetch("/api/models/list");
    renderModelResult(await response.json());
  });
}

if (modelActiveButton) {
  modelActiveButton.addEventListener("click", async () => {
    const response = await fetch("/api/models/active");
    renderModelResult(await response.json());
  });
}

if (modelSetButton) {
  modelSetButton.addEventListener("click", async () => {
    const modelId = modelIdInput?.value?.trim();
    if (!modelId) return;
    const response = await fetch("/api/models/set-active", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: modelId }),
    });
    renderModelResult(await response.json());
  });
}

if (modelDriftButton) {
  modelDriftButton.addEventListener("click", async () => {
    try {
      const baseline = JSON.parse(modelDriftBaseline?.value || "[]");
      const current = JSON.parse(modelDriftCurrent?.value || "[]");
      const response = await fetch("/api/models/drift-check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ baseline, current }),
      });
      renderModelResult(await response.json());
    } catch (err) {
      renderModelResult({ error: String(err) });
    }
  });
}

if (modelShadowButton) {
  modelShadowButton.addEventListener("click", async () => {
    try {
      const candidateId = modelShadowCandidate?.value?.trim();
      const activeId = modelShadowActive?.value?.trim();
      const features = JSON.parse(modelShadowFeatures?.value || "[]");
      const target = JSON.parse(modelShadowTarget?.value || "[]");
      const response = await fetch("/api/models/shadow-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_model_id: candidateId,
          active_model_id: activeId || undefined,
          features,
          target,
        }),
      });
      renderModelResult(await response.json());
    } catch (err) {
      renderModelResult({ error: String(err) });
    }
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
