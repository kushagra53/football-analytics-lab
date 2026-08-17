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

