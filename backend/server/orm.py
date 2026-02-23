import csv
import logging
import math

from .db import get_conn, put_conn
from .settings import CSV_PATH

log = logging.getLogger(__name__)


def setup_db() -> None:
    """Create the hypertable and seed it from CSV if empty."""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meter_readings (
                time        TIMESTAMPTZ NOT NULL,
                meterusage  DOUBLE PRECISION NOT NULL
            );
        """)

        cur.execute("""
            SELECT create_hypertable(
                'meter_readings', 'time',
                if_not_exists => TRUE,
                migrate_data   => TRUE
            );
        """)

        cur.execute("SELECT COUNT(*) FROM meter_readings;")
        result = cur.fetchone()
        count = result[0] if result else 0

        if count == 0:
            _seed(cur)
        else:
            log.info("Database already contains %d rows – skipping seed.", count)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur is not None:
            cur.close()
        put_conn(conn)


def _seed(cur) -> None:
    log.info("Seeding database from %s …", CSV_PATH)
    rows = []
    with open(CSV_PATH, newline="") as f:
        for row in csv.DictReader(f):
            try:
                val = float(row["meterusage"])
                if not math.isnan(val):
                    rows.append((row["time"], val))
            except (ValueError, KeyError):
                pass
    cur.executemany(
        "INSERT INTO meter_readings (time, meterusage) VALUES (%s, %s);", rows
    )
    log.info("Inserted %d rows.", len(rows))


def get_readings() -> list[tuple]:
    """Return all meter readings ordered by time."""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT time, meterusage FROM meter_readings ORDER BY time;")
        return cur.fetchall()
    finally:
        if cur is not None:
            cur.close()
        put_conn(conn)
