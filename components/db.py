from __future__ import annotations

import pandas as pd

from PYTHON.utils.config import get_db_connection


def run_query(query: str, params: tuple | list | None = None) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()


def run_query_with_connection(
    query: str,
    connection,
    params: tuple | list | None = None,
) -> pd.DataFrame:
    return pd.read_sql(query, connection, params=params)
