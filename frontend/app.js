const leagueInput = document.querySelector("#league");
const bookmakersInput = document.querySelector("#bookmakers");
const jurisdictionInput = document.querySelector("#jurisdiction");
const jurisdictionStatus = document.querySelector("#jurisdiction-status");
const useDeviceLocationButton = document.querySelector("#use-device-location");
const deviceLocationStatus = document.querySelector("#device-location-status");
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
const oddsPanel = document.querySelector("#odds-panel");
const insightsPanel = document.querySelector("#insights-panel");
const tabButtons = document.querySelectorAll(".tab-button");
const insightMatchup = document.querySelector("#insight-matchup");
const insightStatus = document.querySelector("#insight-status");
const insightResult = document.querySelector("#insight-result");

let selectedImageUrl = null;
let trackingSource = "manual";
let selectedGameTime = "";
const upcomingGames = new Map();
let displayedSportsbooks = [];
let jurisdictionSource = "manual";

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

function readableSportsbooks() {
  const configured = bookmakersInput.value
    .split(",")
    .map((name) => name.trim())
    .filter(Boolean)
    .map((name) => name.replaceAll("_", " "));
  const names = displayedSportsbooks.length ? displayedSportsbooks : configured;
  return names.length ? names.join(", ") : "the selected sportsbook providers";
}

function jurisdictionMessage() {
  const books = readableSportsbooks();
  const selectedOption = jurisdictionInput.options[jurisdictionInput.selectedIndex];
  if (!jurisdictionInput.value) {
    return `Research view only. Choose a U.S. state or D.C., or use device location to suggest one, before treating lines from ${books} as actionable.`;
  }
  const source = jurisdictionSource === "device" ? "was suggested from device location" : "selected";
  return `${selectedOption.text} ${source}. Lines shown from ${books} are research context—not proof that a provider is licensed or available there. Confirm each book's current eligibility, age rules, and account requirements before placing any wager.`;
}

function updateJurisdictionStatus() {
  jurisdictionStatus.textContent = jurisdictionMessage();
  jurisdictionStatus.classList.toggle("selected", Boolean(jurisdictionInput.value));
}

function setDeviceLocationStatus(message, isError = false) {
  deviceLocationStatus.textContent = message;
  deviceLocationStatus.classList.toggle("error", isError);
}

function locationErrorMessage(error) {
  if (error?.code === error.PERMISSION_DENIED) return "Device location was not shared. You can choose any state manually.";
  if (error?.code === error.TIMEOUT) return "Device location took too long. Try again or choose a state manually.";
  return "Device location could not be determined. Choose a state manually.";
}

async function suggestJurisdictionFromDevice(position) {
  const response = await fetch("/jurisdiction/device", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      latitude: Number(position.coords.latitude.toFixed(3)),
      longitude: Number(position.coords.longitude.toFixed(3)),
    }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Unable to suggest a state from device location.");
  if (!jurisdictionInput.querySelector(`option[value="${data.code}"]`)) {
    throw new Error("The suggested state is not available in the selector. Choose a state manually.");
  }
  jurisdictionInput.value = data.code;
  jurisdictionSource = "device";
  updateJurisdictionStatus();
  setDeviceLocationStatus(`${data.name} was suggested from your device location. You can still choose a different state manually.`);
}

function useDeviceLocation() {
  if (!navigator.geolocation) {
    setDeviceLocationStatus("This browser cannot provide device location. Choose a state manually.", true);
    return;
  }
  useDeviceLocationButton.disabled = true;
  setDeviceLocationStatus("Requesting browser permission for a one-time state suggestion…");
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        await suggestJurisdictionFromDevice(position);
      } catch (error) {
        setDeviceLocationStatus(error.message, true);
      } finally {
        useDeviceLocationButton.disabled = false;
      }
    },
    (error) => {
      setDeviceLocationStatus(locationErrorMessage(error), true);
      useDeviceLocationButton.disabled = false;
    },
    { enableHighAccuracy: false, maximumAge: 300000, timeout: 10000 },
  );
}

function setActiveTab(tab) {
  const showInsights = tab === "insights";
  oddsPanel.hidden = showInsights;
  insightsPanel.hidden = !showInsights;
  tabButtons.forEach((button) => {
    const selected = button.dataset.tab === tab;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
}

function formatMetric(value, suffix = "") {
  const number = Number(value);
  if (value === null || value === undefined || value === "" || Number.isNaN(number)) return "—";
  const rounded = Number.isInteger(number) ? String(number) : number.toFixed(1);
  return `${rounded}${suffix}`;
}

function formatSignedMetric(value) {
  const formatted = formatMetric(value);
  return formatted !== "—" && Number(value) > 0 ? `+${formatted}` : formatted;
}

function nbaSeasonLabel(season) {
  const year = Number(season);
  return Number.isInteger(year) ? `${year}–${String(year + 1).slice(-2)}` : "Prior season";
}

function average(values) {
  const usable = values.map(Number).filter(Number.isFinite);
  if (!usable.length) return null;
  return usable.reduce((sum, value) => sum + value, 0) / usable.length;
}

function addInsightSection(container, title, metrics, variant = "") {
  const section = document.createElement("section");
  section.className = `insight-section ${variant}`.trim();
  const heading = document.createElement("h4");
  heading.textContent = title;
  const list = document.createElement("div");
  list.className = "insight-metrics";
  metrics.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "insight-metric";
    row.classList.toggle("injury-metric", label === "Reported injury");
    const labelElement = document.createElement("span");
    labelElement.textContent = label;
    const valueElement = document.createElement("strong");
    valueElement.textContent = value;
    row.append(labelElement, valueElement);
    list.append(row);
  });
  section.append(heading, list);
  container.append(section);
}

function hasReportedInjury(availability) {
  const status = String(availability || "").trim().toLowerCase();
  if (!status) return false;
  return ![
    "no current injury report returned",
    "availability data unavailable",
    "available",
    "active",
    "healthy",
  ].includes(status);
}

function playerMetrics(players) {
  return players.flatMap((player) => {
    const metrics = [[
      player.name,
      `${player.position} · ${formatMetric(player.points_per_game)} PTS · ${formatMetric(player.rebounds_per_game)} REB · ${formatMetric(player.assists_per_game)} AST`,
    ]];
    if (hasReportedInjury(player.availability)) {
      metrics.push(["Reported injury", `${player.name}: ${player.availability}`]);
    }
    return metrics;
  });
}

function createTeamHeader(team, side) {
  const header = document.createElement("header");
  header.className = "insight-team-header";
  const label = document.createElement("span");
  label.className = "insight-team-role";
  label.textContent = side;
  const heading = document.createElement("h3");
  heading.textContent = team.team;
  header.append(label, heading);
  return header;
}

function createNflTeamInsightCard(team, side) {
  const card = document.createElement("article");
  card.className = "insight-team";
  card.append(createTeamHeader(team, side));

  const qb = team.quarterback;
  addInsightSection(card, "Quarterback", qb ? [
    ["Starter by passing yards", qb.name],
    ["Passing yards", `${formatMetric(qb.passing_yards)} · ${formatMetric(qb.passing_yards_per_game, " / game")}`],
    ["Passing TD / INT", `${formatMetric(qb.passing_touchdowns)} / ${formatMetric(qb.passing_interceptions)}`],
    ["Rushing yards", `${formatMetric(qb.rushing_yards)} · ${formatMetric(qb.rushing_yards_per_game, " / game")}`],
    ["Rushing TD", formatMetric(qb.rushing_touchdowns)],
    ["Sacks taken", formatMetric(qb.sacks_taken)],
  ] : [["Status", "No qualifying quarterback record returned"]], "quarterback-section");

  addInsightSection(card, "Offense", [
    ["Points per game", formatMetric(team.offense.points_per_game)],
    ["Pass yards per game", formatMetric(team.offense.passing_yards_per_game)],
    ["Rush yards per game", formatMetric(team.offense.rushing_yards_per_game)],
    ["Sacks allowed per game", formatMetric(team.offense.sacks_allowed_per_game)],
    ["Touchdowns per game", formatMetric(team.offense.touchdowns_per_game)],
    ["Red-zone TD rate", formatMetric(team.offense.red_zone_touchdown_rate, "%")],
  ]);
  addInsightSection(card, "Defense", [
    ["Points allowed per game", formatMetric(team.defense.points_allowed_per_game)],
    ["Pass yards allowed per game", formatMetric(team.defense.passing_yards_allowed_per_game)],
    ["Rush yards allowed per game", formatMetric(team.defense.rushing_yards_allowed_per_game)],
    ["Sacks per game", formatMetric(team.defense.sacks_per_game)],
    ["Interceptions per game", formatMetric(team.defense.interceptions_per_game)],
    ["Opp. red-zone TD rate", formatMetric(team.defense.red_zone_touchdown_rate_allowed, "%")],
  ]);
  return card;
}

function createNbaTeamInsightCard(team, side) {
  const card = document.createElement("article");
  card.className = "insight-team";
  card.append(createTeamHeader(team, side));

  addInsightSection(card, "Team averages", [
    ["Games", formatMetric(team.games)],
    ["Points per game", formatMetric(team.offense.points_per_game)],
    ["Field-goal percentage", formatMetric(team.offense.field_goal_percentage, "%")],
    ["Three-point percentage", formatMetric(team.offense.three_point_percentage, "%")],
    ["Rebounds per game", formatMetric(team.offense.rebounds_per_game)],
    ["Assists per game", formatMetric(team.offense.assists_per_game)],
    ["Turnovers per game", formatMetric(team.offense.turnovers_per_game)],
  ]);
  addInsightSection(card, "Efficiency & possession", [
    ["Free-throw percentage", formatMetric(team.offense.free_throw_percentage, "%")],
    ["Free-throw attempts / game", formatMetric(team.offense.free_throw_attempts_per_game)],
    ["Three-point attempts / game", formatMetric(team.offense.three_point_attempts_per_game)],
    ["Assist / turnover", formatMetric(team.offense.assist_to_turnover_ratio)],
    ["Offensive rebounds / game", formatMetric(team.offense.offensive_rebounds_per_game)],
    ["Defensive rebounds / game", formatMetric(team.offense.defensive_rebounds_per_game)],
  ]);
  addInsightSection(card, "Defense", [
    ["Points allowed per game", formatMetric(team.defense.points_allowed_per_game)],
    ["Steals per game", formatMetric(team.defense.steals_per_game)],
    ["Blocks per game", formatMetric(team.defense.blocks_per_game)],
    ["Opponent field-goal percentage", formatMetric(team.defense.opponent_field_goal_percentage, "%")],
  ]);

  const form = team.form || {};
  const record = form.wins === null || form.wins === undefined || form.losses === null || form.losses === undefined
    ? "—"
    : `${formatMetric(form.wins)}-${formatMetric(form.losses)}`;
  addInsightSection(card, "Completed-game form", [
    ["Record", record],
    ["Win percentage", formatMetric(form.win_percentage, "%")],
    ["Last five", Array.isArray(form.recent_form) && form.recent_form.length ? form.recent_form.join(" · ") : "—"],
    ["Point differential / game", formatSignedMetric(form.point_differential_per_game)],
    ["Recent points / allowed", `${formatMetric(form.recent_points_per_game)} / ${formatMetric(form.recent_points_allowed_per_game)}`],
  ]);

  const historical = team.historical_player_context;
  const historicalPlayers = historical?.players || [];
  const players = team.notable_players || [];
  const usesRosterFallback = team.notable_players_source === "previous_season_roster";
  const playerMetricsWithContext = usesRosterFallback
    ? [["Data context", `Current roster confirmed; ${nbaSeasonLabel(historical?.season)} player production is shown because live player statistics are unavailable.`], ...playerMetrics(players)]
    : players.length
      ? playerMetrics(players)
      : [["Status", "No player statistics were returned"]];
  addInsightSection(
    card,
    usesRosterFallback ? `Players to watch · ${nbaSeasonLabel(historical?.season)} context` : "Notable players",
    playerMetricsWithContext,
    "player-section",
  );

  if (historical && !usesRosterFallback) {
    const historicalMetrics = !historical.roster_verified
      ? [["Status", "Past-season player stats are hidden because the current roster could not be confirmed."]]
      : historicalPlayers.length
        ? [
          ["Context", "Prior-season production for players confirmed on the current roster."],
          ...historicalPlayers.map((player) => [
            player.name,
            `${player.position} · ${formatMetric(player.points_per_game)} PTS · ${formatMetric(player.rebounds_per_game)} REB · ${formatMetric(player.assists_per_game)} AST`,
          ]),
        ]
        : [["Status", "No current-roster players had prior-season statistics returned."]];
    addInsightSection(card, `Returning players · ${nbaSeasonLabel(historical.season)}`, historicalMetrics, "player-section historical-section");
  }
  return card;
}

function consensusMarketPoint(event, marketKey, outcomeName) {
  const points = (event.bookmakers || []).flatMap((bookmaker) => (bookmaker.markets || []))
    .filter((market) => market.key === marketKey)
    .flatMap((market) => market.outcomes || [])
    .filter((outcome) => outcome.name === outcomeName)
    .map((outcome) => outcome.point);
  return average(points);
}

function marketComparison(event, summary) {
  const candidates = [];
  const totalLine = consensusMarketPoint(event, "totals", "Over");
  if (summary.estimated_total !== null && totalLine !== null) {
    const gap = summary.estimated_total - totalLine;
    candidates.push({
      strength: Math.abs(gap),
      label: `${gap >= 0 ? "Over" : "Under"} ${totalLine.toFixed(1)}`,
      detail: `The scoring blend is ${summary.estimated_total.toFixed(1)} versus a ${totalLine.toFixed(1)} consensus total.`,
    });
  }
  const homeSpread = consensusMarketPoint(event, "spreads", event.home_team);
  if (summary.estimated_home_margin !== null && homeSpread !== null) {
    const gap = summary.estimated_home_margin + homeSpread;
    candidates.push({
      strength: Math.abs(gap),
      label: `${gap >= 0 ? event.home_team : event.away_team} spread`,
      detail: `The scoring blend's home margin is ${summary.estimated_home_margin.toFixed(1)} versus the home spread of ${homeSpread > 0 ? "+" : ""}${homeSpread.toFixed(1)}.`,
    });
  }
  const strongest = candidates.sort((first, second) => second.strength - first.strength)[0];
  if (!strongest || strongest.strength < 2.5) {
    return "No clear model-to-market gap was found from the current consensus spread or total. Review the matchup; do not force a wager.";
  }
  return `Strongest model-to-market signal: ${strongest.label}. ${strongest.detail} This is a research lead, not a guaranteed or personalized bet.`;
}

function seasonForGame(game) {
  const date = new Date(game.commence_time);
  const startsPreviousCalendarYear = game.league === "nfl" ? date.getUTCMonth() <= 2 : date.getUTCMonth() <= 5;
  return String(date.getUTCFullYear() - (startsPreviousCalendarYear ? 1 : 0));
}

function createMatchupSummary(data, game) {
  const summary = document.createElement("article");
  summary.className = "insight-summary";
  const heading = document.createElement("h3");
  heading.textContent = "Transparent matchup context";
  const scorecard = document.createElement("div");
  scorecard.className = "insight-scorecard";
  scorecard.innerHTML = `
    <div><span>Home</span><strong>${escapeHtml(data.home.team)}</strong><b>${formatMetric(data.matchup_summary.estimated_home_points)}</b></div>
    <div class="scorecard-total"><span>Scoring blend</span><strong>${formatMetric(data.matchup_summary.estimated_total)} total</strong><i>Season-to-date</i></div>
    <div><span>Away</span><strong>${escapeHtml(data.away.team)}</strong><b>${formatMetric(data.matchup_summary.estimated_away_points)}</b></div>`;
  const estimate = document.createElement("p");
  estimate.textContent = `Scoring blend: ${data.home.team} ${formatMetric(data.matchup_summary.estimated_home_points)} — ${data.away.team} ${formatMetric(data.matchup_summary.estimated_away_points)}.`;
  const method = document.createElement("p");
  method.textContent = data.matchup_summary.method;
  const market = document.createElement("p");
  market.textContent = marketComparison(game, data.matchup_summary);
  const jurisdiction = document.createElement("p");
  jurisdiction.className = "jurisdiction-insight-note";
  jurisdiction.textContent = jurisdictionMessage();
  const disclaimer = document.createElement("p");
  disclaimer.textContent = data.matchup_summary.disclaimer;
  summary.append(heading, scorecard, estimate, method, market, jurisdiction, disclaimer);
  return summary;
}

function displayNflInsights(data, game) {
  insightResult.replaceChildren();
  const grid = document.createElement("div");
  grid.className = "insight-team-grid";
  grid.append(createNflTeamInsightCard(data.home, "Home team"), createNflTeamInsightCard(data.away, "Away team"));
  const summary = createMatchupSummary(data, game);
  insightResult.append(grid, summary);
}

function displayNbaInsights(data, game) {
  insightResult.replaceChildren();
  const grid = document.createElement("div");
  grid.className = "insight-team-grid";
  grid.append(createNbaTeamInsightCard(data.home, "Home team"), createNbaTeamInsightCard(data.away, "Away team"));
  const summary = createMatchupSummary(data, game);
  insightResult.append(grid, summary);
}

async function showTeamInsights(game) {
  setActiveTab("insights");
  insightMatchup.textContent = `${game.away_team} at ${game.home_team}`;
  insightResult.replaceChildren();
  setInlineStatus(insightStatus, `Loading authorized ${game.league.toUpperCase()} team data…`);
  const query = new URLSearchParams({
    home_team: game.home_team,
    away_team: game.away_team,
    season: seasonForGame(game),
  });
  try {
    const response = await fetch(`/insights/${game.league}?${query}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Unable to load ${game.league.toUpperCase()} team insights.`);
    if (!data.available) {
      setInlineStatus(insightStatus, data.reason || `API-Sports ${game.league.toUpperCase()} has not been configured for this app.`, true);
      return;
    }
    if (game.league === "nfl") displayNflInsights(data, game);
    else displayNbaInsights(data, game);
    setInlineStatus(insightStatus, `Season-to-date ${data.season} context from ${data.source}. Responses are cached for ${data.cache_minutes} minutes to preserve plan usage.`);
  } catch (error) {
    setInlineStatus(insightStatus, error.message, true);
  }
}

function formatGameTime(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function displayVenueContext(context, scheduledGame = null, requestedGameTime = "") {
  venueResult.replaceChildren();
  const { venue } = context;
  const values = [
    `${context.home_team} home venue: ${venue.venue}`,
    venue.city,
  ];
  if (scheduledGame) {
    values.unshift(`Scheduled game: ${scheduledGame.away_team} at ${scheduledGame.home_team} — ${formatGameTime(scheduledGame.commence_time)}`);
  } else if (requestedGameTime) {
    values.unshift(`Game time selected for venue context: ${formatGameTime(requestedGameTime)}`);
  }
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

function findUpcomingHomeGame(homeTeam = venueHomeTeam.value, league = venueLeague.value) {
  return [...upcomingGames.entries()]
    .filter(([, game]) => game.league === league && game.home_team === homeTeam)
    .sort(([, first], [, second]) => new Date(first.commence_time) - new Date(second.commence_time))[0] || null;
}

function matchHomeTeamToUpcomingGame() {
  const match = findUpcomingHomeGame();
  if (!match) return null;
  const [key, game] = match;
  upcomingGame.value = key;
  selectedGameTime = game.commence_time;
  venueGameTime.value = "";
  return game;
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
  const selectedUpcomingGame = upcomingGames.get(upcomingGame.value);
  const matchedGame = selectedUpcomingGame || (!selectedGameTime && !venueGameTime.value ? matchHomeTeamToUpcomingGame() : null);
  const gameTime = selectedGameTime || venueGameTime.value;
  const submitButton = venueForm.querySelector("button");
  submitButton.disabled = true;
  venueResult.replaceChildren();
  setInlineStatus(venueStatus, `Resolving ${homeTeam}'s home venue…`);
  try {
    const query = new URLSearchParams({ home_team: homeTeam });
    if (gameTime) query.set("game_time_local", gameTime);
    const response = await fetch(`/venue-context/${venueLeague.value}?${query}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Unable to resolve this home venue.");
    displayVenueContext(data, matchedGame, gameTime);
    setInlineStatus(
      venueStatus,
      data.weather?.model_note || data.weather_unavailable || (matchedGame
        ? `Using the official scheduled date: ${formatGameTime(matchedGame.commence_time)}.`
        : "No matching upcoming home game is loaded, so no date or weather was guessed."),
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

function displayEvent(event, league) {
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
          <button class="secondary-button venue-event-button" type="button" data-home-team="${escapeHtml(event.home_team)}" data-league="${escapeHtml(league)}" data-commence-time="${escapeHtml(event.commence_time)}">Use home venue</button>
          <button class="secondary-button insight-event-button" type="button" data-event-key="${escapeHtml(`${league}:${event.id}`)}">Analyze matchup</button>
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
    displayedSportsbooks = [...new Set(
      data.events.flatMap((event) => (event.bookmakers || []).map((bookmaker) => bookmaker.title)).filter(Boolean),
    )];
    updateJurisdictionStatus();
    populateUpcomingGames(data.events, league);
    eventsContainer.innerHTML = data.events.map((event) => displayEvent(event, league)).join("");
    insightMatchup.textContent = "Choose a matchup";
    insightResult.replaceChildren();
    setInlineStatus(insightStatus, "Choose Analyze matchup on an NFL or NBA game to load its authorized team data.");
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
jurisdictionInput.addEventListener("change", () => {
  jurisdictionSource = "manual";
  updateJurisdictionStatus();
});
useDeviceLocationButton.addEventListener("click", useDeviceLocation);

tabButtons.forEach((button) => {
  button.addEventListener("click", () => setActiveTab(button.dataset.tab));
});

venueLeague.addEventListener("change", () => loadVenueTeams());
leagueInput.addEventListener("change", () => {
  selectedGameTime = "";
  venueLeague.value = leagueInput.value;
  loadVenueTeams();
});

venueHomeTeam.addEventListener("change", async () => {
  selectedGameTime = "";
  upcomingGame.value = "";
  venueGameTime.value = "";
  const matchedGame = matchHomeTeamToUpcomingGame();
  await showVenueContext();
  if (matchedGame) {
    setInlineStatus(venueStatus, `Matched ${matchedGame.away_team} at ${matchedGame.home_team} on ${formatGameTime(matchedGame.commence_time)}. ${venueStatus.textContent}`);
  }
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
  const insightAction = event.target.closest(".insight-event-button");
  if (insightAction) {
    const game = upcomingGames.get(insightAction.dataset.eventKey);
    if (game) await showTeamInsights(game);
    return;
  }
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
updateJurisdictionStatus();
resetUpcomingGames();
loadVenueTeams();
loadTrackingEntries();
