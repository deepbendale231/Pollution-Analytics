from __future__ import annotations

from typing import Any

import pandas as pd

from PYTHON.utils.config import get_db_connection


def run_query(query: str, params: tuple[Any, ...] | None = None) -> pd.DataFrame:
    connection = get_db_connection()
    try:
        return pd.read_sql(query, connection, params=params)
    finally:
        connection.close()
