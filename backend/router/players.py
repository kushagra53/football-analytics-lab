from fastapi import APIRouter, HTTPException
from scripts.loading.db import get_connection
from psycopg2.extras import RealDictCursor
from backend.schemas import Player, PlayerStats

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

@router.get("/search")
def search_players(name:str):
    conn= get_connection()
    cursor=conn.cursor(cursor_factory=RealDictCursor)

    query="""
        SELECT 
            player_id,
            player_name,
            player_country,
            preferred_foot
        FROM players
        WHERE player_name ILIKE %s
        LIMIT 10
        """

    cursor.execute(query, (f"%{name}%",))

    player=cursor.fetchall()

    cursor.close()
    conn.close()

    return player




@router.get("/{player_id}", response_model=Player)
def get_player(player_id: int):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
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
        WHERE p.player_id = %s
    """, (player_id,))

    player_seasons = cursor.fetchall()

# this is to merge seasons of a single player, if a player has a single season 

    if not player_seasons:
        raise HTTPException(status_code=404, detail="Player not found")

    player = player_seasons[0]

    seasons = []

    for rows in player_seasons:
        seasons.append({
            "team_id": rows["team_id"],
            "league": rows["league"],
            "season": rows["season"],
            "position": rows["position"],
            "age": rows["age"],
            "minutes_played": rows["minutes_played"]
        })


    cursor.close()
    conn.close()

    return {
    "player_id": player["player_id"],
    "player_name": player["player_name"],
    "player_country": player["player_country"],
    "height": player["height"],
    "preferred_foot": player["preferred_foot"],
    "seasons": seasons
}

@router.get("/{player_id}/stats", response_model=PlayerStats)
def get_playerstats(player_id: int, league: str, season: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
    SELECT
    ps.goals,
    ps.assists,
    ps.expected_goals,
    ps.expected_assists,
    ps.goals_assists_sum,
    ps.total_shots,
    ps.shots_on_target,
    ps.successful_dribbles,
    ps.tackles,
    ps.interceptions,
    ps.clearances,
    ps.key_passes,
    ps.minutes_played,
    ps.rating
    FROM player_season_stats ps
    WHERE ps.player_id = %s
    AND ps.league = %s
    AND ps.season = %s
    """

    cursor.execute(query, (player_id, league, season))
    stats = cursor.fetchone()

    cursor.close()
    conn.close()

    if stats is None:
        raise HTTPException(status_code=404, detail="cmon dude why would i add irrelevant player to the dataset")

    return stats



    
