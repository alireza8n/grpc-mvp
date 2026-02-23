import os

from dotenv import load_dotenv

load_dotenv()

# Database
DB_HOST = os.environ.get("DB_HOST", "timescaledb")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "metrics")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")

# Connection pool
DB_POOL_MIN_CONN = int(os.environ.get("DB_POOL_MIN_CONN", "1"))
DB_POOL_MAX_CONN = int(os.environ.get("DB_POOL_MAX_CONN", "10"))

# Data
CSV_PATH = os.environ.get("CSV_PATH", "/data/meterusage.csv")

# gRPC server
GRPC_PORT = int(os.environ.get("GRPC_PORT", "50051"))
GRPC_WORKERS = int(os.environ.get("GRPC_WORKERS", "10"))
