DROP TABLE IF EXISTS teams CASCADE;

CREATE TABLE teams (
    team_id   INTEGER PRIMARY KEY,
    team_name TEXT NOT NULL ,
    league    TEXT
);