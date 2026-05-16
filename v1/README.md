# maymayinvest — v1

First iteration. Not committed to as the final shape.

## Stack
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, vectorbt, alpaca-py
- Frontend: Next.js 14 + TS (skeleton only in Phase 1)
- Data: PostgreSQL + TimescaleDB (via docker-compose)
- Observability: structlog (JSON) + Prometheus `/metrics`

## Layout
```
backend/   # FastAPI app — see backend/app/
frontend/  # Next.js dashboard (skeleton)
infra/     # docker-compose, Postgres init
docs/      # architecture + design notes
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for module map, design decisions, invariants, and phased roadmap.

## Phase 1 quickstart (after first commit)

```bash
# from v1/
docker compose -f infra/docker-compose.yml up -d        # postgres+timescale
cd backend
uv sync                                                 # installs deps
cp .env.example .env                                    # set ALPACA_API_KEY etc
uv run alembic upgrade head                             # baseline migration
uv run uvicorn app.main:app --reload                    # http://localhost:8000

# sanity
curl http://localhost:8000/healthz
curl http://localhost:8000/metrics
curl http://localhost:8000/api/v1/portfolio             # operator capability
```

## Status
- Phase 1 scaffolding in progress.
- `operator` surface live for `get_portfolio` first; further capabilities incremental.
