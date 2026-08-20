from fastapi import APIRouter, HTTPException
from scripts.loading.db import get_connection
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/leaderboard")

@router.get("")
def get_leaderboard(stat:str, league:str | None=None , season:str | None= None):

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    allowed_stats={
        "goals": "ps.goals",
        "assists": "ps.assists",
        "rating": "ps.rating"
    }
    if stat not in allowed_stats:
        raise HTTPException(status_code=400, detail="If you wish to see insights like that better pay up for the data it ain't free, HAIL CAPITALISM")

    column = allowed_stats[stat]

    query = f"""
    SELECT
        p.player_id,
        p.player_name,
        {column} AS stat_value
    FROM players p
    JOIN player_season_stats ps
        ON p.player_id = ps.player_id
    """
    condition = []
    params = []

    if league is not None:
        condition.append("ps.league = %s")
        params.append(league)

    if season is not None:
        condition.append("ps.season = %s")
        params.append(season)

    if condition:
        query += " WHERE " + " AND ".join(condition)

    query += f"ORDER BY {column} DESC LIMIT 10" 

    cursor.execute(query, tuple(params))
    leaderboard= cursor.fetchall()

    cursor.close()
    conn.close()

    return leaderboard



    