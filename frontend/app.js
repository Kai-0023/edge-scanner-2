const leagueInput = document.querySelector("#league");
const bookmakersInput = document.querySelector("#bookmakers");
const refreshButton = document.querySelector("#refresh");
const status = document.querySelector("#status");
const summary = document.querySelector("#summary");
const eventsContainer = document.querySelector("#events");
const detectLocationButton = document.querySelector("#detect-location");
const checkLocationButton = document.querySelector("#check-location");
const regionCodeInput = document.querySelector("#region-code");
const confirmRegionInput = document.querySelector("#confirm-region");
const locationStatus = document.querySelector("#location-status");
const slipImageInput = document.querySelector("#slip-image");
const slipPreview = document.querySelector("#slip-preview");
const scanSlipButton = document.querySelector("#scan-slip");
const scanStatus = document.querySelector("#scan-status");
const trackingForm = document.querySelector("#tracking-form");
const trackingStatus = document.querySelector("#tracking-status");
const trackingList = document.querySelector("#tracking-list");
const trackingLeague = document.querySelector("#tracking-league");
const trackingEvent = document.querySelector("#tracking-event");
const trackingSelection = document.querySelector("#tracking-selection");
const trackingOdds = document.querySelector("#tracking-odds");
const trackingStake = document.querySelector("#tracking-stake");
const trackingNotes = document.querySelector("#tracking-notes");

let selectedImageUrl = null;
let trackingSource = "manual";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setInlineStatus(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
}

function displayMarkets(markets = []) {
  return markets
    .map((market) => {
      const outcomes = (market.outcomes || [])
        .map((outcome) => {
          const point = outcome.point === undefined ? "" : ` ${outcome.point > 0 ? "+" : ""}${outcome.point}`;
          return `<li><span>${escapeHtml(outcome.name)}${point}</span><strong>${escapeHtml(outcome.price)}</strong></li>`;
        })
        .join("");
      return `<div class="market"><h4>${escapeHtml(market.key)}</h4><ul>${outcomes}</ul></div>`;
    })
    .join("");
}

function displayEvent(event) {
  const bookmakers = (event.bookmakers || [])
    .map(
      (bookmaker) => `
        <article class="bookmaker">
          <div class="bookmaker-title">
            <h3>${escapeHtml(bookmaker.title)}</h3>
            <span>${new Date(bookmaker.last_update).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</span>
          </div>
          ${displayMarkets(bookmaker.markets)}
        </article>`,
    )
    .join("");

  return `
    <article class="event-card">
      <div class="event-heading">
        <div>
          <p class="event-time">${new Date(event.commence_time).toLocaleString()}</p>
          <h2>${escapeHtml(event.away_team)} <span>at</span> ${escapeHtml(event.home_team)}</h2>
        </div>
      <span class="comparison-count">${event.bookmakers?.length || 0} books</span>
      </div>
      <div class="bookmaker-grid">${bookmakers || "<p>No selected sportsbook lines are available for this event.</p>"}</div>
    </article>`;
}

async function loadOdds() {
  const league = leagueInput.value;
  const bookmakers = bookmakersInput.value.trim();
  const query = bookmakers ? `?bookmakers=${encodeURIComponent(bookmakers)}` : "";

  refreshButton.disabled = true;
  refreshButton.textContent = "Loading…";
  status.textContent = "Requesting authorized live odds…";
  status.classList.remove("error");
  summary.hidden = true;
  eventsContainer.innerHTML = "";

  try {
    const response = await fetch(`/live/${league}${query}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load odds.");
    if (data.status === "Live odds are disabled.") throw new Error(data.reason);

    status.textContent = data.cached
      ? "Showing a recent cached response to preserve API credits."
      : "Live lines loaded from your authorized provider.";
    summary.hidden = false;
    summary.innerHTML = `
      <span><strong>${data.event_count}</strong> events</span>
      <span><strong>${data.usage.requests_remaining ?? "—"}</strong> credits remaining</span>
      <span>Markets: ${data.markets.join(", ")}</span>`;
    eventsContainer.innerHTML = data.events.map(displayEvent).join("");
  } catch (error) {
    status.textContent = `Could not load odds: ${error.message}`;
    status.classList.add("error");
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh lines";
  }
}

refreshButton.addEventListener("click", loadOdds);

detectLocationButton.addEventListener("click", () => {
  if (!navigator.geolocation) {
    setInlineStatus(locationStatus, "This browser does not provide device location. You can still enter a state code manually.", true);
    return;
  }

  detectLocationButton.disabled = true;
  detectLocationButton.textContent = "Checking…";
  navigator.geolocation.getCurrentPosition(
    () => {
      setInlineStatus(locationStatus, "Location confirmed on this device. Coordinates were not sent or saved—enter and confirm your state code to continue.");
      detectLocationButton.disabled = false;
      detectLocationButton.textContent = "Location confirmed";
    },
    () => {
      setInlineStatus(locationStatus, "Location permission was not granted. You can still enter a state code manually.", true);
      detectLocationButton.disabled = false;
      detectLocationButton.textContent = "Detect on this device";
    },
    { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
  );
});

checkLocationButton.addEventListener("click", async () => {
  const regionCode = regionCodeInput.value.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(regionCode)) {
    setInlineStatus(locationStatus, "Enter a two-letter state code, such as LA.", true);
    return;
  }
  if (!confirmRegionInput.checked) {
    setInlineStatus(locationStatus, "Confirm that the state code is accurate before continuing.", true);
    return;
  }

  checkLocationButton.disabled = true;
  try {
    const response = await fetch("/compliance/location-research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ region_code: regionCode, confirmed_by_user: true }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to check the research notice.");
    setInlineStatus(locationStatus, `${data.region_code}: ${data.notice} ${data.location_storage}`);
  } catch (error) {
    setInlineStatus(locationStatus, error.message, true);
  } finally {
    checkLocationButton.disabled = false;
  }
});

slipImageInput.addEventListener("change", () => {
  const [file] = slipImageInput.files;
  if (selectedImageUrl) URL.revokeObjectURL(selectedImageUrl);
  selectedImageUrl = null;
  slipPreview.hidden = true;
  trackingSource = "manual";

  if (!file) return;
  selectedImageUrl = URL.createObjectURL(file);
  slipPreview.src = selectedImageUrl;
  slipPreview.hidden = false;
  setInlineStatus(scanStatus, "Image selected. You can read it with OCR or enter the fields yourself.");
});

scanSlipButton.addEventListener("click", async () => {
  const [file] = slipImageInput.files;
  if (!file) {
    setInlineStatus(scanStatus, "Choose a slip image first, or enter the fields manually.", true);
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    setInlineStatus(scanStatus, "Use an image smaller than 5 MB.", true);
    return;
  }

  scanSlipButton.disabled = true;
  scanSlipButton.textContent = "Reading…";
  try {
    const formData = new FormData();
    formData.append("image", file);
    const response = await fetch("/tracking/ocr", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "OCR could not read this image.");
    if (data.suggestions.american_odds !== null) trackingOdds.value = data.suggestions.american_odds;
    if (data.suggestions.stake !== null) trackingStake.value = data.suggestions.stake;
    trackingSource = "ocr_confirmed";
    setInlineStatus(scanStatus, "OCR suggestions were added. Review every field before saving; the image and OCR text will not be stored.");
  } catch (error) {
    trackingSource = "manual";
    setInlineStatus(scanStatus, `${error.message} You can still enter the fields manually.`, true);
  } finally {
    scanSlipButton.disabled = false;
    scanSlipButton.textContent = "Read image with OCR";
  }
});

function optionalNumber(input) {
  const value = input.value.trim();
  return value ? Number(value) : null;
}

function displayTrackingEntries(entries) {
  trackingList.replaceChildren();
  entries.forEach((entry) => {
    const item = document.createElement("li");
    const metadata = [entry.league.toUpperCase(), entry.american_odds ?? "odds not entered", entry.stake === null ? "stake not entered" : `$${entry.stake}`];
    item.textContent = `${entry.event_name} — ${entry.selection} (${metadata.join(" · ")})`;
    trackingList.append(item);
  });
}

async function loadTrackingEntries() {
  try {
    const response = await fetch("/tracking/entries");
    const data = await response.json();
    if (response.ok) displayTrackingEntries(data.entries);
  } catch {
    // Tracking is optional, so a failed list refresh should not interrupt the dashboard.
  }
}

trackingForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const odds = optionalNumber(trackingOdds);
  const stake = optionalNumber(trackingStake);
  if ((odds !== null && !Number.isInteger(odds)) || (stake !== null && Number.isNaN(stake))) {
    setInlineStatus(trackingStatus, "Enter whole-number American odds and a valid stake, or leave them blank.", true);
    return;
  }

  const payload = {
    league: trackingLeague.value,
    event_name: trackingEvent.value.trim(),
    selection: trackingSelection.value.trim(),
    american_odds: odds,
    stake,
    notes: trackingNotes.value.trim() || null,
    source: trackingSource,
  };
  try {
    const response = await fetch("/tracking/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to save this entry.");
    setInlineStatus(trackingStatus, "Reviewed entry saved locally. The image and raw OCR text were not saved.");
    trackingForm.reset();
    trackingSource = "manual";
    if (selectedImageUrl) URL.revokeObjectURL(selectedImageUrl);
    selectedImageUrl = null;
    slipPreview.removeAttribute("src");
    slipPreview.hidden = true;
    await loadTrackingEntries();
  } catch (error) {
    setInlineStatus(trackingStatus, error.message, true);
  }
});

loadOdds();
loadTrackingEntries();
