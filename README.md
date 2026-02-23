# gRPC Meter Usage Service

A containerised, gRPC-based microservice system that ingests time-series electricity consumption data from a CSV file, stores it in TimescaleDB, and exposes it through an HTTP + HTML frontend.

---

## Architecture

```
             ┌─────────────┐
             │   Browser   │
             └──────┬──────┘
                    │ HTTP GET /
                    │ HTTP GET /api/metrics
             ┌──────▼──────┐
             │  frontend   │  Python (http.server)  :8000
             └──────┬──────┘
                    │ gRPC GetMetrics
             ┌──────▼──────┐
             │ grpc-server │  Python (grpcio)        :50051
             └──────┬──────┘
                    │ SQL
             ┌──────▼──────┐
             │ timescaledb │  TimescaleDB (pg16)     :5432
             └─────────────┘
```

1. **timescaledb** – PostgreSQL with the TimescaleDB extension. Stores meter readings in a hypertable partitioned by time.
2. **grpc-server** – On startup reads `meterusage.csv`, creates the hypertable, seeds the database, then serves the `GetMetrics` RPC.
3. **frontend** – Lightweight HTTP server that proxies the gRPC call and returns JSON; also serves the single-page HTML dashboard.

---

## How to Run

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2 (included with Docker Desktop)

### Start

```bash
docker compose up --build
```

Wait until you see `gRPC server listening on port 50051` and `HTTP server listening on port 8000` in the logs (roughly 30–60 s on first run while TimescaleDB initialises).

| Service     | URL / address         |
|-------------|-----------------------|
| HTML dashboard | <http://localhost:8000> |
| JSON API    | <http://localhost:8000/api/metrics> |
| gRPC server | `localhost:50051`     |
| TimescaleDB | `localhost:5432`      |

### Stop

```bash
docker compose down
```

### Makefile

A `Makefile` is provided as a convenience wrapper. Run `make help` to list all targets:

```
$ make help
  up                 Start all services (build if needed)
  up-detach          Start all services in the background
  down               Stop and remove containers
  down-volumes       Stop containers and delete volumes (resets DB)
  logs               Follow logs for all services
  logs-backend       Follow logs for the gRPC server
  logs-frontend      Follow logs for the frontend
  build              Rebuild all Docker images without starting
  ps                 Show running containers
  venv               Create the virtual environment
  install            Install backend runtime + test dependencies
  test               Run unit tests
  test-cov           Run tests with coverage report
  proto              Regenerate protobuf stubs for both services
  help               Show this help message
```

---

## Tests

Unit tests cover the three backend layers (`db`, `orm`, `servicer`) using `unittest` + `pytest`. All external dependencies (psycopg2, gRPC context) are mocked so no running database is required.

### Setup

```bash
make install   # creates .venv and installs runtime + test deps
```

Or manually:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-test.txt
```

### Run

```bash
make test          # run all tests
make test-cov      # run with coverage report
```

Or directly with pytest:

```bash
cd backend && ../.venv/bin/pytest tests/ -v
```

### Test structure

```
backend/
  tests/
    test_db.py        # wait_for_db, init_pool, close_pool, get_conn, put_conn
    test_orm.py       # get_readings, setup_db, _seed
    test_servicer.py  # MetricsServicer.GetMetrics
```

---

## Tech Stack

| Layer        | Technology                  | Why                                                             |
|--------------|-----------------------------|-----------------------------------------------------------------|
| Backend      | Python 3.12 + grpcio        | Concise gRPC implementation; minimal boilerplate               |
| Database     | TimescaleDB (PostgreSQL 16) | Native time-series support (hypertables, compression, queries) |
| DB driver    | psycopg2-binary             | Mature, zero-dependency PostgreSQL adapter                     |
| Frontend     | Python 3.12 stdlib          | No extra runtime needed; http.server is sufficient for this use case |
| Orchestration | Docker Compose v2           | Single-command spin-up; matches assignment deliverables        |

---

## Design Decisions

- **Proto-first**: A single `metrics.proto` file drives both the server and the client; protobuf stubs are generated at Docker build time with `grpc_tools.protoc`, so no pre-generated files need to be committed.
- **`GetMetrics` request uses a typed `Empty` message instead of the well-known `google.protobuf.Empty`**: The RPC is defined as `GetMetrics(Empty) returns (MetricsResponse)` using a local `Empty` message with no fields. This preserves forward-compatibility — fields can be added to the request later (e.g. filters, pagination) without a breaking change to the service contract.
- **Database connection pool**: psycopg2's `ThreadedConnectionPool` is used instead of opening a new connection per request. This avoids hammering the database with connection overhead under concurrent gRPC calls and keeps the number of open connections bounded by `DB_POOL_MAX_CONN`.
- **Reused gRPC stub + multithreaded frontend**: The frontend creates the gRPC channel and stub once at startup and shares them across all HTTP requests, handled by Python's `ThreadingHTTPServer`. This avoids the latency of re-establishing the channel on every request and allows the frontend to handle multiple in-flight gRPC calls concurrently without queuing.
- **TimescaleDB instead of plain PostgreSQL**: TimescaleDB was chosen to stay close to a real-world IoT/time-series stack. It provides native hypertable partitioning by time, which scales to billions of rows without manual sharding — a natural fit for meter data — while avoiding the overhead of building a hand-rolled in-memory store.
- **Layered backend architecture**: The server code is split into `settings.py`, `db.py`, `orm.py`, and `servicer.py` rather than a single file. Each layer has a single responsibility (config, connection management, data access, RPC handling), making the code easier to read, test in isolation, and extend.
- **No pagination**: The current dataset is small and fully fits in a single response. Pagination was deliberately omitted to keep the implementation simple; the `Empty` request message can be extended with `page_size` / `page_token` fields in a future iteration without a breaking proto change.
- **Idempotent seeding**: The backend checks whether the table is empty before inserting rows, making restarts safe without data duplication.
- **Health-check dependency**: The `grpc-server` uses `depends_on: condition: service_healthy` to wait for TimescaleDB's `pg_isready` check before starting, removing the need for an external entrypoint script. The backend also has its own retry loop for extra robustness.
- **No persistent volume for DB**: Per the requirements, TimescaleDB data lives only inside the container; the database is re-seeded on every `docker compose up`.
- **Zero frontend framework**: The HTML page uses only vanilla JS (`fetch` + DOM manipulation) to keep the implementation minimal and dependency-free.
- **CSV mounted as read-only**: `meterusage.csv` is bind-mounted into the backend container at `/data/meterusage.csv` (read-only) so the original file is never modified.
- **Vibe-coding prompt preserved**: The initial prompt used to scaffold the repository with an AI coding assistant is kept in `vibe-coding/cursor-prompt.md` for transparency and reproducibility.

---

## Backend Environment Variables

The gRPC backend supports the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `timescaledb` | PostgreSQL/TimescaleDB host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `metrics` | Database name |
| `DB_USER` | `postgres` | Database username |
| `DB_PASS` | `postgres` | Database password |
| `CSV_PATH` | `/data/meterusage.csv` | CSV file path inside the backend container |
| `DB_POOL_MIN_CONN` | `1` | Minimum open connections in the psycopg2 pool |
| `DB_POOL_MAX_CONN` | `10` | Maximum open connections in the psycopg2 pool |
