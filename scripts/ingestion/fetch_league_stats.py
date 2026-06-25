"""
Fetch full player season statistics (attacking + passing + defending +
possession + discipline) for one league/season from SofaScore, and
write to data/raw/<league>/league_stats.csv

This single script replaces fetch_standard.py / fetch_passing.py /
fetch_defense.py / fetch_possession.py / fetch_misc.py from the
original FBref-based plan -- SofaScore's player-statistics endpoint
returns all of those categories in one response, so there's no need
to split ingestion by stat table anymore.

Usage:
    python fetch_league_stats.py --league premier_league --season 25/26
"""

import argparse
from pathlib import Path

from sofascore_utils import fetch_league_player_stats, save_csv, LEAGUES

TABLE_NAME = "league_stats"

ROOT = Path(__file__).resolve().parents[2]  # repo root (football-analytics-lab/)
RAW_DIR = ROOT / "data" / "raw"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", required=True, choices=sorted(LEAGUES.keys()))
    parser.add_argument("--season", required=True, help="e.g. 25/26")
    parser.add_argument("--max-players", type=int, default=700)
    parser.add_argument(
        "--data-source", default="sofavpn", choices=["sofavpn", "sofascore"],
        help="datafc source to hit. 'sofavpn' (default) routes around api.sofascore.com's "
             "Cloudflare challenge; switch to 'sofascore' if that ever stops being needed.",
    )
    args = parser.parse_args()

    df = fetch_league_player_stats(
        args.league, args.season, max_players=args.max_players, data_source=args.data_source
    )
    save_csv(df, args.league, TABLE_NAME, RAW_DIR)


if __name__ == "__main__":
    main()