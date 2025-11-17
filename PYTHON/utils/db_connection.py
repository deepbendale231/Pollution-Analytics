import mysql.connector
import pandas as pd

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Poojadeep@231",  
        database="air_quality_db"
    )

def run_query(query):
    conn = get_connection()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

if __name__ == "__main__":
    from db_connection import run_query
    df = run_query("SELECT COUNT(*) AS total_records FROM air_quality;")
    print(df)

