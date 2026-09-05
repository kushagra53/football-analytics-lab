from pydantic import BaseModel

class Season(BaseModel):
    team_id: int 
    league: str 
    season: str
    position: str
    age: int
    minutes_played: int

class Player(BaseModel):
    player_id: int
    player_name: str
    player_country: str 
    height: int 
    preferred_foot: str
    seasons: list[Season]

class PlayerStats(BaseModel):
    goals: int
    assists: int
    expected_goals: float | None = None
    expected_assists: float | None = None
    goals_assists_sum: int
    total_shots: int
    shots_on_target: int
    successful_dribbles: float | None = None 
    tackles: float | None = None 
    interceptions: int | None = None 
    clearances: int | None = None 
    key_passes: float | None = None 
    minutes_played: int
    rating: float

class PlayerComaparisionEntry(BaseModel):
    player_id:int
    player_name:str
    stats:PlayerStats

class PlayerComparisions(BaseModel):
    player1:PlayerComaparisionEntry
    player2:PlayerComaparisionEntry

