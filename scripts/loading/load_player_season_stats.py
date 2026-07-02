import pandas as pd
from pathlib import Path

from db import get_connection

DATA_DIR = Path("data/processed")


def load_player_season_stats():
    conn = get_connection()
    cur = conn.cursor()

    exclude = {
        "player_name",
        "team_name",
        "player_country",
        "height",
        "preferred_foot",
    }

    for csv_path in DATA_DIR.glob("*/players.csv"):
        print(f"Loading {csv_path} into database...")

        df = pd.read_csv(csv_path)

        columns = [col for col in df.columns if col not in exclude]

        column_names = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))

        query = f"""
        INSERT INTO player_season_stats ({column_names})
        VALUES ({placeholders})
        ON CONFLICT (player_id, league, season)
        DO NOTHING;
        """

        for index, row in df.iterrows():
            values = tuple(
                None if pd.isna(row[col]) else row[col]
                for col in columns
            )

            try:
                cur.execute(query, values)
            except Exception:
                print(f"Failed in {csv_path} at row {index}")
                raise

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    load_player_season_stats()