from fastapi import APIRouter
from scripts.loading.db import get_connection

router= APIRouter(prefix="/players")

@router.get("")
def get_players(position: str | None = None):
    conn= get_connection()
    cursor = conn.cursor()

    if position is None:
        cursor.execute("""
            SELECT     
            p.player_id,
            p.name,
            p.nationality,
            p.height,
            p.preferred_foot,
            ps.team_id,
            ps.league,
            ps.season,
            ps.position,
            ps.age,
            ps.minutes
            FROM players p
            JOIN player_season_stats ps
            ON p.player_id = ps.player_id
        """)
    else:
        cursor.execute("""
            SELECT     
            p.player_id,
            p.name,
            p.nationality,
            p.height,
            p.preferred_foot,
            ps.team_id,
            ps.league,
            ps.season,
            ps.position,
            ps.age,
            ps.minutes
            FROM players p
            JOIN player_season_stats ps
            ON p.player_id = ps.player_id
            WHERE ps.position = %s
        """, (position,))

    players = cursor.fetchall()
    cursor.close()
    conn.close()
    return players

@router.get("/{player_id}")
def get_player(player_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
    "SELECT * FROM players WHERE player_id = %s",
    (player_id,) #Python tuples with one element need a trailing comma.
)
    player= cursor.fetchone()
    cursor.close()
    conn.close()
    return player


