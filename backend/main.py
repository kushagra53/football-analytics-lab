from fastapi import FastAPI
from .database import get_connection
from .router import players
from .router import teams
from .router import leaderboard
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(players.router)
app.include_router(teams.router)
app.include_router(leaderboard.router)

@app.get("/")
def read_root():
    return {"status": "API is running!"}

@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        conn.close()
        return {"status": "healthy"}
    except Exception as e:
        print(f"DATABASE ERROR: {repr(e)}", flush=True)
        raise HTTPException(
            status_code=503,
            detail="Database unavailable"
        )








