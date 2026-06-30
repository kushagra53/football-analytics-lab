"""
Fetch squad rosters (position, age, nationality, height) from SofaScore
for a league. Run this *in addition to* fetch_league_stats.py -- the
player-stats endpoint only returns stat fields, no bio/position data.

Why this is its own script rather than bolted onto fetch_league_stats.py:
the bio/position data lives on a per-team roster endpoint
(standings_data -> squad_data), a different shape of call than the
per-league stats pull, so it's a separate raw table (squad.csv) that
gets joined in during cleaning, not during ingestion.

Known limitation: squad_data() gives broad position groups only
(Goalkeeper/Defender/Midfielder/Forward) -- not CB vs full-back detail.
That detail lives on a per-player profile endpoint, which would mean
500+ extra calls per league. Skipped for v1; revisit as a "Stage 8"
upgrade once the rest of the pipeline is proven out.

Usage:
    python fetch_squad.py --league premier_league --season 25/26
"""

import argparse
from pathlib import Path

from datafc import standings_data, squad_data

from sofascore_utils import save_csv, resolve_season_id, LEAGUES, DEFAULT_DATA_SOURCE

TABLE_NAME = "squad"
ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"


def fetch_squads_for_league(league: str, season_label: str, data_source: str = DEFAULT_DATA_SOURCE):
    tournament_id = LEAGUES[league]
    season_id = resolve_season_id(tournament_id, season_label, data_source=data_source)

    # standings_data() lists every team in the league; squad_data() then
    # loops over each of those teams internally (its own rate limiting).
    standings_df = standings_data(tournament_id, season_id, data_source=data_source)
    df = squad_data(standings_df, data_source=data_source)

    df["league"] = league
    df["season"] = season_label
    return df, standings_df


def authoritative_teams(standings_df, league: str, season_label: str):
    """The real N teams competing in the league this season -- used to filter
    out promotion/relegation PLAYOFF sides (e.g. Saint-Etienne, Rodez AF in
    Ligue 1 25/26) that SofaScore tags under the same tournament/season_id
    even though those clubs play in the division below. Same issue applies
    to Bundesliga's 16th vs Bundesliga-2-3rd playoff -- not Ligue-1-specific."""
    total_df = standings_df[standings_df["category"] == "Total"]
    teams = total_df[["team_id", "team_name"]].drop_duplicates(subset="team_id").copy()
    teams["league"] = league
    teams["season"] = season_label
    return teams


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", required=True, choices=sorted(LEAGUES.keys()))
    parser.add_argument("--season", required=True, help="e.g. 25/26")
    parser.add_argument("--data-source", default=DEFAULT_DATA_SOURCE, choices=["sofavpn", "sofascore"])
    args = parser.parse_args()

    df, standings_df = fetch_squads_for_league(args.league, args.season, data_source=args.data_source)
    save_csv(df, args.league, TABLE_NAME, RAW_DIR)

    teams_df = authoritative_teams(standings_df, args.league, args.season)
    save_csv(teams_df, args.league, "teams", RAW_DIR)


if __name__ == "__main__":
    main()