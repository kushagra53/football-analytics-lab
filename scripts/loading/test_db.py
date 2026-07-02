from db import get_connection

conn = get_connection()
print("Connection established successfully!")

conn.close()    