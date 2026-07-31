from fastapi import APIRouter
from scripts.loading.db import get_connection

router = APIRouter(prefix="/leaderboard")