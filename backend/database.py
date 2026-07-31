import psycopg2
from psycopg2.extra import RealDictCursor 
# RealDictCursor allows us to get results as dictionaries instead of tuples which makes it easier to work with JSON files.

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="football_analytics",
        user="postgres",
        password="kusu9247",
        cursor_factory=RealDictCursor,
        port=5432
    )
    return conn