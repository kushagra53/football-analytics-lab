from fastapi import APIRouter
from scripts.loading.db import get_connection
from psycopg2.extras import RealDictCursor

router= APIRouter(prefix="/players")

@router.get("")
def get_players(
    position: str | None = None,
    league: str | None = None,
    team_id: int | None = None,
    min_minutes: int | None = None,
):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
    SELECT
        p.player_id,
        p.player_name,
        p.player_country,
        p.height,
        p.preferred_foot,
        ps.team_id,
        ps.league,
        ps.season,
        ps.position,
        ps.age,
        ps.minutes_played
    FROM players p
    JOIN player_season_stats ps
    ON p.player_id = ps.player_id
    """

    conditions = []
    params = []

    if position is not None:
        conditions.append("ps.position = %s")
        params.append(position)

    if league:
        conditions.append("ps.league = %s")
        params.append(league)

    if team_id:
        conditions.append("ps.team_id = %s")
        params.append(team_id)

    if min_minutes:
        conditions.append("ps.minutes_played >= %s")
        params.append(min_minutes)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    cursor.execute(query, tuple(params))

    players = cursor.fetchall()

    cursor.close()
    conn.close()

    return players


