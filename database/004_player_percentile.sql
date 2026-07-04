DROP TABLE IF EXISTS player_season_stats CASCADE;

CREATE TABLE player_percentile(
player_id INTEGER REFERENCES players(player_id),
metric TEXT NOT NULL,
cohort TEXT NOT NULL,
percentile DOUBLE PRECISION,
UNIQUE(player_id,metric,cohort)	
);