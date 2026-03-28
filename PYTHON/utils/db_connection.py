from components.db import run_query
from PYTHON.utils.config import get_db_connection


def get_connection():
    return get_db_connection()

if __name__ == "__main__":
    from db_connection import run_query
    df = run_query("SELECT COUNT(*) AS total_records FROM air_quality;")
    print(df)

