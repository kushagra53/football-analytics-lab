"""
Clean & transform raw SofaScore pulls into one analysis-ready table per
league: data/raw/<league>/{league_stats,squad}.csv -> data/processed/<league>/players.csv

What this script does, and why:

1. Multi-team players (mid-season transfers): league_stats.csv may have
   more than one row for the same player_id if SofaScore splits stats
   per team played for. We don't assume this can't happen -- we detect
   duplicates and merge them: counting stats (goals, tackles, etc.) are
   summed, rate/percentage stats are minutes-weighted-averaged, and the
   team column becomes a "team_a / team_b" joined string with a
   multi_team flag, so it's visible rather than silently overwritten.

2. Per-90 math happens HERE, once, on raw totals -- not pulled
   pre-divided from the API. Every counting stat gets an explicit
   `_per90` column; rate stats (rating, pass completion %, etc.) are
   already per-event and are left as-is.

3. Position/age/nationality come from squad.csv (a different endpoint,
   see fetch_squad.py) and are left-joined on player_id. A player can
   legitimately have no match here (e.g. departed the squad since the
   stats snapshot) -- that shows up as NaN position, not a dropped row.

4. Minutes threshold is a FLAG (`meets_minutes_threshold`), not a
   filter -- low-minute players stay in the table (their per-90 numbers
   are just noisier), so the percentile engine can decide later whether
   to exclude them from a cohort rather than that decision being made
   silently here.

Usage:
    python clean_data.py --league premier_league
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("clean_data")

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

DEFAULT_MIN_MINUTES = 600  # ~6-7 full matches; configurable via --min-minutes

# Counting stats: summed across multi-team rows, divided by minutes for per90.
COUNT_FIELDS = [
    "goals", "assists", "expectedGoals", "expectedAssists", "goalsAssistsSum",
    "penaltyGoals", "freeKickGoal", "totalShots", "shotsOnTarget",
    "bigChancesCreated", "bigChancesMissed", "accuratePasses", "keyPasses",
    "accurateLongBalls", "successfulDribbles", "tackles", "interceptions",
    "clearances", "possessionLost", "yellowCards", "redCards", "saves",
    "appearances",
]

# Rate/percentage stats: minutes-weighted-averaged across multi-team rows,
# NOT divided by minutes again (they're already per-event rates).
RATE_FIELDS = [
    "rating", "accuratePassesPercentage", "accurateLongBallsPercentage",
    "successfulDribblesPercentage", "scoringFrequency", "goalsPrevented",
]

# Always summed, never averaged, never divided (it IS the minutes denominator).
MINUTES_FIELD = "minutesPlayed"


def _snake_case(name: str) -> str:
    out = []
    for ch in name:
        if ch.isupper() and out:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def merge_multi_team_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse duplicate player_id rows (mid-season transfers within
    the same league) into one row per player, flagging that it happened."""
    dup_ids = df["player_id"][df["player_id"].duplicated(keep=False)].unique()
    if len(dup_ids) == 0:
        df["multi_team"] = False
        return df

    log.info(f"Found {len(dup_ids)} player(s) with multiple team rows -- merging.")

    kept_rows = []
    for player_id, group in df.groupby("player_id", sort=False):
        if len(group) == 1:
            row = group.iloc[0].to_dict()
            row["multi_team"] = False
            kept_rows.append(row)
            continue

        merged = {"player_id": player_id, "player_name": group["player_name"].iloc[0]}
        merged["team_name"] = " / ".join(group["team_name"].astype(str).unique())
        merged["team_id"] = group["team_id"].iloc[-1]  # most recent listed = last row
        merged["multi_team"] = True

        total_minutes = group[MINUTES_FIELD].sum()
        merged[MINUTES_FIELD] = total_minutes

        for field in COUNT_FIELDS:
            if field in group.columns:
                merged[field] = group[field].sum()

        for field in RATE_FIELDS:
            if field in group.columns:
                if total_minutes > 0:
                    weights = group[MINUTES_FIELD].fillna(0)
                    merged[field] = (group[field].fillna(0) * weights).sum() / total_minutes
                else:
                    merged[field] = group[field].mean()

        # carry through non-stat metadata from the row with the most minutes played
        primary = group.loc[group[MINUTES_FIELD].idxmax()]
        for col in ("league", "season", "scraped_at", "tournament_id", "season_id"):
            if col in group.columns:
                merged[col] = primary[col]

        kept_rows.append(merged)

    return pd.DataFrame(kept_rows)


def add_per90_columns(df: pd.DataFrame) -> pd.DataFrame:
    """For every counting stat, add a `<field>_per90` column. NaN (not 0)
    when minutes is 0, so it's visibly "no sample" rather than implying
    "zero rate"."""
    per90_denominator = df[MINUTES_FIELD].replace(0, pd.NA) / 90
    for field in COUNT_FIELDS:
        if field in df.columns:
            df[f"{field}_per90"] = df[field] / per90_denominator
    return df


def load_squad(league: str) -> pd.DataFrame:
    squad_path = RAW_DIR / league / "squad.csv"
    if not squad_path.exists():
        log.warning(
            f"{squad_path} not found -- position/age/nationality will be missing. "
            f"Run fetch_squad.py for '{league}' to add them."
        )
        return pd.DataFrame(columns=["player_id", "position", "age", "player_country", "height"])

    squad_df = pd.read_csv(squad_path)
    keep_cols = ["player_id", "position", "age", "player_country", "height", "preferred_foot"]
    return squad_df[[c for c in keep_cols if c in squad_df.columns]].drop_duplicates(subset="player_id")


def clean_league(league: str, min_minutes: int = DEFAULT_MIN_MINUTES) -> pd.DataFrame:
    stats_path = RAW_DIR / league / "league_stats.csv"
    if not stats_path.exists():
        raise FileNotFoundError(f"{stats_path} not found -- run fetch_league_stats.py for '{league}' first.")

    df = pd.read_csv(stats_path)
    log.info(f"Loaded {len(df)} raw rows for {league}")

    df = merge_multi_team_rows(df)
    log.info(f"{len(df)} rows after multi-team merge")

    df = add_per90_columns(df)

    squad_df = load_squad(league)
    df = df.merge(squad_df, on="player_id", how="left")

    df["meets_minutes_threshold"] = df[MINUTES_FIELD] >= min_minutes

    df.columns = [_snake_case(c) for c in df.columns]

    # stable, readable column order: identity -> minutes -> per90 metrics -> raw totals -> rates -> meta
    id_cols = [c for c in ("player_id", "player_name", "team_name", "team_id", "position",
                           "age", "player_country", "height", "preferred_foot",
                           "league", "season") if c in df.columns]
    minutes_cols = [c for c in ("minutes_played", "appearances", "meets_minutes_threshold", "multi_team") if c in df.columns]
    per90_cols = sorted(c for c in df.columns if c.endswith("_per90"))
    rate_cols = [_snake_case(f) for f in RATE_FIELDS if _snake_case(f) in df.columns]
    raw_count_cols = [_snake_case(f) for f in COUNT_FIELDS if _snake_case(f) in df.columns and _snake_case(f) not in minutes_cols]
    other_cols = [c for c in df.columns if c not in id_cols + minutes_cols + per90_cols + rate_cols + raw_count_cols]

    ordered = id_cols + minutes_cols + per90_cols + rate_cols + raw_count_cols + other_cols
    return df[ordered]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", required=True)
    parser.add_argument("--min-minutes", type=int, default=DEFAULT_MIN_MINUTES)
    args = parser.parse_args()

    df = clean_league(args.league, min_minutes=args.min_minutes)

    out_dir = PROCESSED_DIR / args.league
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "players.csv"
    df.to_csv(out_path, index=False)
    log.info(f"Saved {len(df)} cleaned rows -> {out_path}")


if __name__ == "__main__":
    main()