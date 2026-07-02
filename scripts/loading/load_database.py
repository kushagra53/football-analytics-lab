import pandas as pd
from db import get_connection
from pathlib import Path

DATA_DIR = Path("data/processed")



def load_players():
    conn = get_connection()
    cur = conn.cursor()
    
    for csv_path in DATA_DIR.glob("*/players.csv"):
        print(f"Loading {csv_path} into database...")
        df= pd.read_csv(csv_path)
        

        for index, row in df.iterrows():
            values = (
            int(row["player_id"]),
            row["player_name"],
            row["player_country"],
            None if pd.isna(row["height"]) else int(row["height"]),
            row["preferred_foot"],
        )

            try:
              cur.execute(
            """
            INSERT INTO players
            (player_id, player_name, player_country, height, preferred_foot)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (player_id)
            DO NOTHING;
            """,
            values,
        )
            except Exception as e:
               print(f"Failed in {csv_path} at row {index}")
               print(values)
               raise

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    load_players()