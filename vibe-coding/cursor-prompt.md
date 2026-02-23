## ✅ Improved Prompt

Based on `task/assignment.pdf`, implement the following system.

### 📁 Project Structure

Create a project with this structure:

```
/backend
/frontend
/task
docker-compose.yml
README.md
```

---

## 🐳 Docker Compose Requirements

Create a `docker-compose.yml` with **three services**:

1. **grpc-server** (backend)
2. **frontend** (HTTP server + static HTML)
3. **timescaledb**

### Configuration Requirements

* Do NOT mount database data to a local volume.
* Expose ports:

  * Backend (gRPC): `50051`
  * Frontend (HTTP): `8000`
  * TimescaleDB: `5432`
* Backend service path should include `meterusage.csv`.

---

## 🖥 Backend (gRPC Server)

Implement a gRPC server (language of your choice) that:

1. On startup:

   * Reads `meterusage.csv`
   * Creates a table in TimescaleDB
   * Inserts the CSV records into the database

2. Exposes one RPC method:

### RPC: `GetMetrics`

* Request: empty
* Response format:

```json
{
  "data": [
    {
      "time": "timestamp",
      "meterusage": 55.09
    }
  ]
}
```

* The data must be fetched from TimescaleDB.

---

## 🌐 Frontend (HTTP + HTML)

Implement:

### 1️⃣ HTTP Server

* Calls the gRPC server
* Returns JSON in this format:

```json
{
  "data": [
    {
      "time": "timestamp",
      "meterusage": 55.09
    }
  ]
}
```

### 2️⃣ Single Page HTML

* Simple HTML page
* Fetches JSON from the HTTP server
* Renders the data inside a basic `<table>`
* Keep implementation minimal (no frameworks)

---

## 📄 Task Description

Build a language-independent, gRPC-based microservice system:

1. A gRPC server that serves time-based electricity consumption data from `meterusage.csv`.
2. An HTTP server that calls the gRPC service and returns the data as JSON.
3. A single-page HTML document that fetches and displays the data.

---

## 📦 Deliverables

* Public Git repository
* `README.md` explaining:

  * Architecture
  * How to run (docker-compose)
  * Tech stack used
  * Design decisions

---

If you want, I can also rewrite it in a **more strict technical-spec style** (better for AI code generation), or in a **shorter high-signal version** optimized specifically for Cursor.
