from fastapi import FastAPI
from scripts.loading.db import get_connection
from .router import players
from .router import teams
from .router import leaderboard

app = FastAPI()

app.include_router(players.router)
app.include_router(teams.router)
app.include_router(leaderboard.router)

@app.get("/")
def read_root():
    return {"status": "API is running!"}









