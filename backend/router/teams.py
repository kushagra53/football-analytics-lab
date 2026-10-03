from fastapi import APIRouter
from ..database import get_connection
from psycopg2.extras import RealDictCursor

router= APIRouter(prefix="/teams")

@router.get("")
def get_teams():
    conn = get_connection()
    cursor= conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return teams

@router.get("/{team_id}")
def get_team(team_id: int):
    conn = get_connection()
    cursor= conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
       "SELECT * FROM teams WHERE team_id = %s",
       (team_id,)
   )
    team = cursor.fetchone()
    cursor.close()
    conn.close()
    return team

@router.get("/{team_id}/players")
def get_team_players(team_id: int, season: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            p.player_id,
            p.player_name,
            p.player_country,
            p.height,
            p.preferred_foot,
            ps.position,
            ps.age,
            ps.minutes_played
        FROM players p
        JOIN player_season_stats ps
            ON p.player_id = ps.player_id
        WHERE ps.team_id = %s
        AND ps.season = %s
    """

    cursor.execute(query, (team_id, season))
    players = cursor.fetchall()

    cursor.close()
    conn.close()

    return players