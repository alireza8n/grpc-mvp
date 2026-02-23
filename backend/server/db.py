import logging
import time

import psycopg2
from psycopg2 import pool

from .settings import (
    DB_HOST,
    DB_NAME,
    DB_PASS,
    DB_POOL_MAX_CONN,
    DB_POOL_MIN_CONN,
    DB_PORT,
    DB_USER,
)

log = logging.getLogger(__name__)

_pool: pool.ThreadedConnectionPool | None = None


def wait_for_db(retries: int = 20, delay: int = 3) -> None:
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
            )
            conn.close()
            log.info("Database is ready.")
            return
        except psycopg2.OperationalError as exc:
            log.warning("Attempt %d/%d – DB not ready: %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Could not connect to the database after %d attempts." % retries)


def init_pool() -> None:
    global _pool
    if _pool is not None:
        return
    _pool = pool.ThreadedConnectionPool(
        minconn=DB_POOL_MIN_CONN,
        maxconn=DB_POOL_MAX_CONN,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )
    log.info(
        "Initialized DB connection pool (min=%d, max=%d).",
        DB_POOL_MIN_CONN,
        DB_POOL_MAX_CONN,
    )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        log.info("Closed DB connection pool.")


def get_conn():
    if _pool is None:
        raise RuntimeError("DB pool is not initialized.")
    return _pool.getconn()


def put_conn(conn) -> None:
    if _pool is not None and conn is not None:
        _pool.putconn(conn)
