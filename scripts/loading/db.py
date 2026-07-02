import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="football_analytics",
        user="postgres",
        password="kusu9247"
    )