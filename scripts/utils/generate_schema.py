import pandas as pd

CSV_PATH = "data/processed/premier_league/players.csv"

df = pd.read_csv(CSV_PATH)

# Columns that already exist in other tables or you've written manually
skip = {
    "player_id",
    "player_name",
    "player_country",
    "height",
    "preferred_foot",
    "team_id",
    "team_name",
    "league",
    "season",
    "position",
    "age"
}

type_map = {
    "int64": "INTEGER",
    "float64": "DOUBLE PRECISION",
    "bool": "BOOLEAN",
    "object": "TEXT"
}

for col, dtype in df.dtypes.items():
    if col in skip:
        continue

    sql_type = type_map.get(str(dtype), "TEXT")
    print(f"    {col} {sql_type},")