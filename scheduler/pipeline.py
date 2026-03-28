from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from DATA.ingestion.fetch_openaq import fetch_openaq_measurements
from DATA.ingestion.load import insert_measurements
from DATA.ingestion.transform import transform_openaq_dataframe
from PYTHON.utils.config import get_db_connection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOGS_DIR / "pipeline.log"

PIPELINE_INTERVAL_HOURS = 6


def _setup_logger() -> logging.Logger:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("scheduler.pipeline")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)

    stream = logging.StreamHandler()
    stream.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(stream)

    return logger


LOGGER = _setup_logger()


def _log_run(status: str, records_fetched: int, records_inserted: int, duration: float, extra: str = "") -> None:
    line = (
        f"{datetime.now().isoformat(timespec='seconds')} | {status} | "
        f"records_fetched={records_fetched} | records_inserted={records_inserted} | duration={duration:.4f}s"
    )
    if extra:
        line = f"{line} | {extra}"
    LOGGER.info(line)


def run_pipeline_once() -> dict[str, Any]:
    start = time.perf_counter()
    records_fetched = 0
    records_inserted = 0

    try:
        raw_df = fetch_openaq_measurements()
        records_fetched = len(raw_df)

        clean_df = transform_openaq_dataframe(raw_df)

        connection = get_db_connection()
        try:
            load_summary = insert_measurements(clean_df, connection)
        finally:
            connection.close()

        records_inserted = int(load_summary.get("inserted", 0))
        duration = time.perf_counter() - start
        _log_run("success", records_fetched, records_inserted, duration)

        return {
            "status": "success",
            "records_fetched": records_fetched,
            "records_inserted": records_inserted,
            "duration_seconds": round(duration, 4),
        }
    except Exception as exc:
        duration = time.perf_counter() - start
        _log_run("failed", records_fetched, records_inserted, duration, extra=f"error={exc}")
        # Do not re-raise; scheduler must keep running.
        return {
            "status": "failed",
            "records_fetched": records_fetched,
            "records_inserted": records_inserted,
            "duration_seconds": round(duration, 4),
            "error": str(exc),
        }


def run_now() -> dict[str, Any]:
    return run_pipeline_once()


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline_once,
        trigger="interval",
        hours=PIPELINE_INTERVAL_HOURS,
        id="pollution_live_ingestion_pipeline",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def main() -> None:
    # Immediate run first, then scheduler.
    run_now()

    scheduler = create_scheduler()
    scheduler.start()

    LOGGER.info(
        f"{datetime.now().isoformat(timespec='seconds')} | scheduler_started | every={PIPELINE_INTERVAL_HOURS}h"
    )

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)
        LOGGER.info(f"{datetime.now().isoformat(timespec='seconds')} | scheduler_stopped")


if __name__ == "__main__":
    main()
