const leagueInput = document.querySelector("#league");
const bookmakersInput = document.querySelector("#bookmakers");
const refreshButton = document.querySelector("#refresh");
const status = document.querySelector("#status");
const summary = document.querySelector("#summary");
const eventsContainer = document.querySelector("#events");
const venueForm = document.querySelector("#venue-form");
const upcomingGame = document.querySelector("#upcoming-game");
const venueLeague = document.querySelector("#venue-league");
const venueHomeTeam = document.querySelector("#venue-home-team");
const venueGameTime = document.querySelector("#venue-game-time");
const venueStatus = document.querySelector("#venue-status");
const venueResult = document.querySelector("#venue-result");
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
let selectedGameTime = "";
const upcomingGames = new Map();

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

function displayVenueContext(context) {
  venueResult.replaceChildren();
  const { venue } = context;
  const values = [
    `${context.home_team} home venue: ${venue.venue}`,
    venue.city,
  ];
  if (context.weather) {
    const conditions = context.weather.conditions;
    values.push(
      `Weather at ${context.weather.forecast_time_local} (${context.weather.timezone || "venue time"})`,
      `${conditions.weather_description}; ${conditions.temperature_f}°F`,
      `Precipitation: ${conditions.precipitation_probability_percent}%`,
      `Wind: ${conditions.wind_speed_mph} mph; gusts ${conditions.wind_gusts_mph} mph`,
      ...context.weather.review_flags,
    );
  }
  if (context.weather_unavailable) values.push(`Weather: ${context.weather_unavailable}`);
  values.forEach((value) => {
    const item = document.createElement("li");
    item.textContent = value;
    venueResult.append(item);
  });
}

function resetUpcomingGames(message = "Load authorized live odds to choose a game") {
  upcomingGames.clear();
  upcomingGame.replaceChildren();
  const option = document.createElement("option");
  option.value = "";
  option.textContent = message;
  upcomingGame.append(option);
  upcomingGame.disabled = true;
}

function populateUpcomingGames(events, league) {
  resetUpcomingGames("Choose an upcoming game from the loaded odds");
  const futureEvents = [...events]
    .filter((event) => new Date(event.commence_time).getTime() >= Date.now() - 60 * 60 * 1000)
    .sort((first, second) => new Date(first.commence_time) - new Date(second.commence_time));
  futureEvents.forEach((event) => {
    const key = `${league}:${event.id}`;
    upcomingGames.set(key, { ...event, league });
    const option = document.createElement("option");
    option.value = key;
    option.textContent = `${new Date(event.commence_time).toLocaleString()} — ${event.away_team} at ${event.home_team}`;
    upcomingGame.append(option);
  });
  upcomingGame.disabled = futureEvents.length === 0;
  if (!futureEvents.length) resetUpcomingGames("No upcoming games were returned by the odds provider");
}

async function loadVenueTeams(preferredTeam = "") {
  const league = venueLeague.value;
  venueHomeTeam.disabled = true;
  venueHomeTeam.replaceChildren();
  setInlineStatus(venueStatus, `Loading ${league.toUpperCase()} home venues…`);
  try {
    const response = await fetch(`/venues/${league}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to load the venue list.");
    data.venues.forEach((venue) => {
      const option = document.createElement("option");
      option.value = venue.team;
      option.textContent = `${venue.team} — ${venue.venue}`;
      venueHomeTeam.append(option);
    });
    if (preferredTeam && [...venueHomeTeam.options].some((option) => option.value === preferredTeam)) {
      venueHomeTeam.value = preferredTeam;
    }
    setInlineStatus(venueStatus, "Select a home team to use its official home venue.");
  } catch (error) {
    setInlineStatus(venueStatus, error.message, true);
  } finally {
    venueHomeTeam.disabled = false;
  }
}

async function showVenueContext() {
  const homeTeam = venueHomeTeam.value;
  if (!homeTeam) {
    setInlineStatus(venueStatus, "Choose a home team first.", true);
    return;
  }
  const submitButton = venueForm.querySelector("button");
  submitButton.disabled = true;
  venueResult.replaceChildren();
  setInlineStatus(venueStatus, `Resolving ${homeTeam}'s home venue…`);
  try {
    const query = new URLSearchParams({ home_team: homeTeam });
    const gameTime = selectedGameTime || venueGameTime.value;
    if (gameTime) query.set("game_time_local", gameTime);
    const response = await fetch(`/venue-context/${venueLeague.value}?${query}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to resolve this home venue.");
    displayVenueContext(data);
    setInlineStatus(
      venueStatus,
      data.weather?.model_note || data.weather_unavailable || "Venue was determined from the home team only; away-team and device locations were not used.",
    );
  } catch (error) {
    setInlineStatus(venueStatus, error.message, true);
  } finally {
    submitButton.disabled = false;
  }
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
        <div class="event-actions">
          <span class="comparison-count">${event.bookmakers?.length || 0} books</span>
          <button class="secondary-button venue-event-button" type="button" data-home-team="${escapeHtml(event.home_team)}" data-league="${leagueInput.value}" data-commence-time="${escapeHtml(event.commence_time)}">Use home venue</button>
        </div>
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
    populateUpcomingGames(data.events, league);
  } catch (error) {
    status.textContent = `Could not load odds: ${error.message}`;
    status.classList.add("error");
    resetUpcomingGames("Connect The Odds API to choose an upcoming game");
  } finally {
    refreshButton.disabled = false;
    refreshButton.textContent = "Refresh lines";
  }
}

refreshButton.addEventListener("click", loadOdds);

venueLeague.addEventListener("change", () => loadVenueTeams());
leagueInput.addEventListener("change", () => {
  selectedGameTime = "";
  venueLeague.value = leagueInput.value;
  loadVenueTeams();
});

venueHomeTeam.addEventListener("change", () => {
  selectedGameTime = "";
  upcomingGame.value = "";
});

venueGameTime.addEventListener("input", () => {
  selectedGameTime = "";
  upcomingGame.value = "";
});

upcomingGame.addEventListener("change", async () => {
  const game = upcomingGames.get(upcomingGame.value);
  if (!game) return;
  venueLeague.value = game.league;
  await loadVenueTeams(game.home_team);
  selectedGameTime = game.commence_time;
  venueGameTime.value = "";
  setInlineStatus(venueStatus, `Selected ${game.away_team} at ${game.home_team} on ${new Date(game.commence_time).toLocaleString()}.`);
  await showVenueContext();
});

venueForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await showVenueContext();
});

eventsContainer.addEventListener("click", async (event) => {
  const action = event.target.closest(".venue-event-button");
  if (!action) return;
  venueLeague.value = action.dataset.league;
  await loadVenueTeams(action.dataset.homeTeam);
  selectedGameTime = action.dataset.commenceTime;
  venueGameTime.value = "";
  await showVenueContext();
  venueForm.scrollIntoView({ behavior: "smooth", block: "center" });
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
resetUpcomingGames();
loadVenueTeams();
loadTrackingEntries();
