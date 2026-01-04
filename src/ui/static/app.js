const refreshButton = document.getElementById("refresh-tests");
const testResults = document.getElementById("test-results");

async function fetchTestCenter() {
  testResults.textContent = "Running checks...";
  try {
    const response = await fetch("/api/test-center/checks");
    const data = await response.json();
    if (!Array.isArray(data)) {
      testResults.textContent = "Unexpected response from Test Center.";
      return;
    }
    testResults.innerHTML = data
      .map(
        (check) =>
          `<div class="test-result ${check.status}">` +
          `<strong>${check.name}</strong> — ${check.status.toUpperCase()}<br/>` +
          `<span>${check.message}</span>` +
          (check.next_step ? `<br/><em>${check.next_step}</em>` : "") +
          "</div>"
      )
      .join("");
  } catch (err) {
    testResults.textContent = `Test Center error: ${err}`;
  }
}

if (refreshButton) {
  refreshButton.addEventListener("click", fetchTestCenter);
}
