# Data Services

Aegix OS should ship with a clear data service suite so agents have predictable storage for memory, indexes, receipts, metrics, queues, and local applications.

## Default storage map

```text
/aegix/data/
  sqlite/
  postgres/
  vector/
  timeseries/
  cache/
  warehouse/
```

## Recommended options

| Need | Default option | Notes |
|---|---|---|
| Local task/app state | SQLite | Best first choice for small durable state and project-local files |
| Durable service DB | Postgres | Best default for multi-user services and API-backed apps |
| Analytics | DuckDB | Good for local reports over files, CSV, Parquet, JSONL, and receipts |
| Cache/queue | Redis-compatible service | Use for ephemeral queues, locks, and short-lived state |
| Vector storage | Qdrant or equivalent | Index over canonical files, not primary memory |
| Time-series storage | Prometheus-compatible service | Metrics, service health, model timings, resource history |

## Vector storage rule

Vector databases are indexes. They should not become hidden primary memory.

Canonical sources should remain:

- Obsidian Markdown
- project files
- receipts
- ADRs
- YAML/JSONL records
- SQLite/Postgres records

## Time-series rule

Time-series storage should capture operational evidence:

- agent session durations
- model latency
- token/cost counters
- service health
- CPU/memory/disk/network metrics
- router/appliance status over time
- failed approval or policy events

## Agent rules

- Prefer SQLite for project-local state until a real service DB is needed.
- Prefer Postgres for shared app/service state.
- Treat vector search as recall support, not truth.
- Treat metrics as evidence for verification and troubleshooting.
- Document DB schema, retention, backup, and restore behavior before agents rely on it.
