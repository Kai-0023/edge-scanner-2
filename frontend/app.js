const leagueInput = document.querySelector("#league");
const bookmakersInput = document.querySelector("#bookmakers");
const refreshButton = document.querySelector("#refresh");
const status = document.querySelector("#status");
const summary = document.querySelector("#summary");
const eventsContainer = document.querySelector("#events");

function displayMarkets(markets = []) {
  return markets
    .map((market) => {
      const outcomes = (market.outcomes || [])
        .map((outcome) => {
          const point = outcome.point === undefined ? "" : ` ${outcome.point > 0 ? "+" : ""}${outcome.point}`;
          return `<li><span>${outcome.name}${point}</span><strong>${outcome.price}</strong></li>`;
        })
        .join("");
      return `<div class="market"><h4>${market.key}</h4><ul>${outcomes}</ul></div>`;
    })
    .join("");
}

function displayEvent(event) {
  const bookmakers = (event.bookmakers || [])
    .map(
      (bookmaker) => `
        <article class="bookmaker">
          <div class="bookmaker-title">
            <h3>${bookmaker.title}</h3>
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
          <h2>${event.away_team} <span>at</span> ${event.home_team}</h2>
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
loadOdds();
