import os
from typing import Any

from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()

REQUIRED_DB_ENV_VARS = [
    "DB_HOST",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_PORT",
]


def _get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None or value.strip() == "":
        raise EnvironmentError(
            f"Missing required environment variable: {var_name}. "
            "Please set it in your environment or .env file."
        )
    return value


def _load_db_config() -> dict:
    missing = [var for var in REQUIRED_DB_ENV_VARS if not os.getenv(var)]
    if missing:
        missing_list = ", ".join(missing)
        raise EnvironmentError(
            f"Missing required database environment variables: {missing_list}. "
            "Please define them in your environment or .env file."
        )

    db_port = _get_required_env("DB_PORT")
    try:
        port = int(db_port)
    except ValueError as exc:
        raise EnvironmentError(
            f"Invalid DB_PORT value '{db_port}'. DB_PORT must be an integer."
        ) from exc

    return {
        "host": _get_required_env("DB_HOST"),
        "user": _get_required_env("DB_USER"),
        "password": _get_required_env("DB_PASSWORD"),
        "database": _get_required_env("DB_NAME"),
        "port": port,
    }


def get_db_connection() -> Any:
    """Return a mysql-connector-python MySQLConnection using environment settings."""
    config = _load_db_config()
    try:
        import mysql.connector  # pyright: ignore[reportMissingImports]
    except ModuleNotFoundError as exc:
        raise ImportError(
            "mysql-connector-python is not installed. Install it with: "
            "pip install mysql-connector-python"
        ) from exc

    return mysql.connector.connect(**config)
