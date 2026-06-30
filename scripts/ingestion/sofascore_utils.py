"""
Shared utilities for pulling player season statistics from SofaScore.

Why SofaScore instead of FBref:
FBref's Opta-sourced advanced stats (tackles, interceptions, passing,
possession -- everything except goals/assists/cards) were permanently
removed in January 2026 after Opta terminated FBref's data license.
SofaScore exposes the same class of metrics through an undocumented but
fairly stable JSON API. We build on top of the `datafc` package, which
already handles the hard parts: Cloudflare-safe TLS impersonation
(via curl_cffi), retries with backoff, and a shared rate limiter.
(pip install datafc)

We still apply our own ingestion discipline on top of that library,
matching what we'd have wanted from FBref:
- player_id captured directly from SofaScore (stable numeric ID --
  no name-matching needed downstream)
- scraped_at timestamp + dated snapshots, so season-over-season /
  week-over-week tracking is possible later without re-fetching history
- fetch RAW TOTALS (accumulation="total"), not pre-computed per-90 --
  so the per-90 math happens once, in our own cleaning stage, with our
  own minutes threshold, not whatever SofaScore's per90 toggle assumes

Known limitation (flagging now, not hiding it): this endpoint does not
return a detailed position (CB vs full-back vs DM, etc.) -- only broad
groups via the filter (G/D/M/F). Detailed position lives on the squad
endpoint (datafc.squad_data(team_id)) and will need to be joined in
during the cleaning stage if/when the percentile engine needs CB-only
cohorts rather than "all defenders."
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from datafc import seasons_data
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.sofascore.fetch_league_player_stats_data import _validate_lps_params
from datafc.sofascore._parsers import parse_league_player_stats_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sofascore_ingest")

# All fields the league_player_stats_data endpoint currently supports.
# Pulled in full ("skip no metric") rather than cherry-picked.
ALL_FIELDS = [
    "goals", "assists", "rating", "expectedGoals", "expectedAssists",
    "goalsAssistsSum", "penaltyGoals", "freeKickGoal", "scoringFrequency",
    "totalShots", "shotsOnTarget", "bigChancesCreated", "bigChancesMissed",
    "accuratePasses", "accuratePassesPercentage", "keyPasses",
    "accurateLongBalls", "accurateLongBallsPercentage",
    "successfulDribbles", "successfulDribblesPercentage",
    "tackles", "interceptions", "clearances", "possessionLost",
    "yellowCards", "redCards", "saves", "goalsPrevented",
    "minutesPlayed", "appearances",
]

# SofaScore unique-tournament IDs for the leagues we plan to support.
# Verified against sofascore.com/football/tournament/<country>/<slug>/<id>
LEAGUES = {
    "premier_league": 17,
    "la_liga": 8,
    "bundesliga": 35,
    "serie_a": 23,
    "ligue_1": 34,
}


DEFAULT_DATA_SOURCE = "sofavpn"  # api.sofascore.com 403s with a Cloudflare
# "challenge" response on this network even from a plain browser request --
# datafc ships api.sofavpn.com as a mirror specifically for this case.
# Switch back to "sofascore" if/when the direct domain stops challenging you.


def resolve_season_id(tournament_id: int, season_label: str, data_source: str = DEFAULT_DATA_SOURCE) -> int:
    """Look up the SofaScore season_id matching a human season label
    like '25/26' or '2025/2026'. Raises with the available options if
    nothing matches, instead of silently grabbing the wrong season."""
    df = seasons_data(tournament_id, data_source=data_source)

    label = season_label.replace("-", "/").strip()
    short_label = "/".join(p[-2:] for p in label.split("/")) if "/" in label else label

    match = df[df["season_year"].astype(str).isin([label, short_label])]
    if match.empty:
        available = df["season_year"].tolist()
        raise ValueError(
            f"No season matching '{season_label}' for tournament_id={tournament_id}. "
            f"Available seasons: {available}"
        )
    return int(match.iloc[0]["season_id"])


def fetch_league_player_stats(
    league: str, season_label: str, max_players: int = 700, data_source: str = DEFAULT_DATA_SOURCE
) -> pd.DataFrame:
    """Fetch every player's season totals for one league/season, across
    every field SofaScore exposes (attacking, passing, defending,
    possession, discipline, GK). Returns one row per player."""
    if league not in LEAGUES:
        raise ValueError(f"Unknown league '{league}'. Choices: {list(LEAGUES)}")

    tournament_id = LEAGUES[league]
    season_id = resolve_season_id(tournament_id, season_label, data_source=data_source)

    log.info(
        f"Fetching {league} ({season_label}) via data_source='{data_source}' -> "
        f"tournament_id={tournament_id}, season_id={season_id}"
    )

    # NOTE: datafc's built-in league_player_stats_data() paginates using a
    # `page=` query param, but the live SofaScore API ignores it and always
    # returns page 1 -- confirmed by direct testing (every "page" returned
    # identical results), which silently produced 100% duplicate rows.
    # The API DOES respect `offset=` (player-count based, not page-based),
    # so we drive pagination ourselves here, reusing datafc's validated
    # field/param handling and response parser.
    validate_source(data_source)
    selected_fields, fields_param = _validate_lps_params(
        accumulation="total", position=None, fields=ALL_FIELDS, order="-minutesPlayed"
    )
    base = API_URLS[data_source]
    page_size = min(max_players, 100)

    records = []
    offset = 0
    with SofascoreClient(rate_limit=2.0) as client:
        while len(records) < max_players:
            url = (
                f"{base}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/statistics"
                f"?limit={page_size}&order=-minutesPlayed&accumulation=total"
                f"&fields={fields_param}&offset={offset}"
            )
            data = client.get(url)
            page_records = parse_league_player_stats_records(data, tournament_id, season_id, selected_fields)
            if not page_records:
                break
            records.extend(page_records)
            if len(page_records) < page_size:
                break  # last page was a partial page -- nothing more to fetch
            offset += page_size

    df = pd.DataFrame(records[:max_players])

    df["league"] = league
    df["season"] = season_label
    df["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return df


def fetch_squad_info(
    league: str, season_label: str, data_source: str = DEFAULT_DATA_SOURCE
) -> pd.DataFrame:
    """Fetch position / age / height / market value for every player in the
    league, via standings_data -> squad_data (one call per team, ~20 calls
    per league -- much cheaper than a per-player profile call for ~600
    players). This is what makes position-grouped percentile cohorts
    (CB vs FB vs everyone-tagged-'D') possible later.

    Note: 'position' here is SofaScore's broad group (G/D/M/F), not a
    detailed sub-position. Detailed positions (CB vs RB, etc.) require a
    separate per-player call (datafc.player_data -> position_detailed) --
    deliberately deferred until the percentile engine actually needs that
    granularity, rather than paying ~600 extra requests for it now.
    """
    if league not in LEAGUES:
        raise ValueError(f"Unknown league '{league}'. Choices: {list(LEAGUES)}")

    tournament_id = LEAGUES[league]
    season_id = resolve_season_id(tournament_id, season_label, data_source=data_source)

    log.info(f"Fetching squad info for {league} ({season_label})")
    standings = standings_data(tournament_id, season_id, data_source=data_source)
    squads = squad_data(standings, data_source=data_source)

    squads["league"] = league
    squads["season"] = season_label
    squads["scraped_at"] = datetime.now(timezone.utc).isoformat()
    return squads

def save_csv(df: pd.DataFrame, league: str, table_name: str, raw_dir: Path, snapshot: bool = True) -> Path:
    """Write the latest CSV (overwritten each run) and a dated snapshot
    copy, so historical seasons / form-over-time stays possible later
    without having to re-fetch."""
    league_dir = raw_dir / league
    league_dir.mkdir(parents=True, exist_ok=True)

    latest_path = league_dir / f"{table_name}.csv"
    df.to_csv(latest_path, index=False)
    log.info(f"Saved {len(df)} rows -> {latest_path}")

    if snapshot:
        snap_dir = league_dir / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        df.to_csv(snap_dir / f"{table_name}_{date_str}.csv", index=False)

    return latest_path




