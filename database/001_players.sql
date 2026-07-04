DROP TABLE IF EXISTS players CASCADE;

CREATE TABLE players (
    player_id   INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    player_country TEXT,
    height     INTEGER,
    preferred_foot TEXT
);