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
          (check.details && check.details.mock_mode ? `<br/><em>MOCK MODE ACTIVE</em>` : "") +
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
    analyzeStatus.textContent = `Orchestrator: ${data.status}`;
  });
}

if (pauseButton) {
  pauseButton.addEventListener("click", async () => {
    const data = await updateOrchestrator("pause");
    analyzeStatus.textContent = `Orchestrator: ${data.status}`;
  });
}

if (stopButton) {
  stopButton.addEventListener("click", async () => {
    const data = await updteOrchestrator("stop");
    analyzeStatus.textContent = `Orchestrator: ${data.status}`;
  });
}

if (saveWatchlistButton) {
  saveWatchlistButton.addEventListener("click", async () => {
it    const payload = { symbols: watchlistInput.value };
    const response = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    watchlistStatus.textContent = data.error
      ? `Error: ${data.error}`
      : `Saved ${data.symbols.length} symbols.`;
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
    analyzeStatus.textContent = data.message || `Processed ${data.processed} symbols.`;
  });
}

if (analyzeAllButton) {
  analyzeAllButton.addEventListener("click", async () => {
    const response = await fetch("/api/analyze/all", { method: "POST" });
    const data = await response.json();
    analyzeStatus.textContent = data.message || `Processed ${data.processed} symbols.`;
  });
}

async function refreshFundingAlerts() {
  if (!fundingAlertsPanel) return;
  const response = await fetch("/api/funding-alerts");
  const data = await response.json();
  if (!Array.isArray(data) || data.length === 0) {
    fundingAlertsPanel.innerHTML = '<div class="alert">No active funding alerts.</div>';
    return;
  }
  fundingAlertsPanel.innerHTML = data
    .map(
      (alert) =>
        `<div class="stacked-item">` +
        `<strong>${alert.symbol}</strong> — Missing cash: $${alert.missing_cash}<br/>` +
        `<span>Actions: ${alert.proposed_actions}</span><br/>` +
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
    logBox.textContent = "No logs yet.";
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
