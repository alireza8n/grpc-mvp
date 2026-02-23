import csv
import math
import os
import time
import logging
from concurrent import futures

import grpc
import psycopg2
import metrics_pb2
import metrics_pb2_grpc

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DB_HOST = os.environ.get("DB_HOST", "timescaledb")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "metrics")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
CSV_PATH = os.environ.get("CSV_PATH", "/data/meterusage.csv")


def wait_for_db(retries=20, delay=3):
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                user=DB_USER, password=DB_PASS
            )
            conn.close()
            log.info("Database is ready.")
            return
        except psycopg2.OperationalError as e:
            log.warning("Attempt %d/%d – DB not ready: %s",
                        attempt, retries, e)
            time.sleep(delay)
    raise RuntimeError(
        "Could not connect to the database after %d attempts." % retries)


def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )


def setup_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meter_readings (
            time        TIMESTAMPTZ NOT NULL,
            meterusage  DOUBLE PRECISION NOT NULL
        );
    """)

    # Make it a TimescaleDB hypertable (idempotent)
    cur.execute("""
        SELECT create_hypertable(
            'meter_readings', 'time',
            if_not_exists => TRUE,
            migrate_data   => TRUE
        );
    """)

    # Only seed if the table is empty
    cur.execute("SELECT COUNT(*) FROM meter_readings;")
    count = cur.fetchone()[0]
    if count == 0:
        log.info("Seeding database from %s …", CSV_PATH)
        with open(CSV_PATH, newline="") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
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
    else:
        log.info("Database already contains %d rows – skipping seed.", count)

    conn.commit()
    cur.close()
    conn.close()


class MetricsServicer(metrics_pb2_grpc.MetricsServiceServicer):
    def GetMetrics(self, request, context):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT time, meterusage FROM meter_readings ORDER BY time;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        data = [
            metrics_pb2.MetricPoint(time=str(row[0]), meterusage=row[1])
            for row in rows
        ]
        return metrics_pb2.MetricsResponse(data=data)


def serve():
    wait_for_db()
    setup_db()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    metrics_pb2_grpc.add_MetricsServiceServicer_to_server(
        MetricsServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    log.info("gRPC server listening on port 50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
