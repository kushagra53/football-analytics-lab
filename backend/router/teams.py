from fastapi import APIRouter
from scripts.loading.db import get_connection

router= APIRouter(prefix="/teams")

@router.get("")
def get_teams():
    conn = get_connection()
    cursor= conn.cursor()
    cursor.execute("SELECT * FROM teams")
    teams = cursor.fetchall()
    cursor.close()
    conn.close()
    return teams

@router.get("/{team_id}")
def get_team(team_id: int):
    conn = get_connection()
    cursor= conn.cursor()
    cursor.execute(
       "SELECT * FROM teams WHERE team_id = %s",
       (team_id,)
   )
    team = cursor.fetchone()
    cursor.close()
    conn.close()
    return team

