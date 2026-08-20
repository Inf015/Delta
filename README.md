# Delta

[![CI](https://github.com/Inf015/Delta/actions/workflows/ci.yml/badge.svg)](https://github.com/Inf015/Delta/actions/workflows/ci.yml)

Telemetry analysis platform for sim racing. It turns a session's raw data into concrete
answers: **where time is lost and which setup change wins it back**.

On a fast lap the margin lives in tenths, and those tenths always come from a number:
braking point, line, traction on exit, brake bias. Delta ingests the telemetry exported
from the simulator, cross-references it with the car's setup, and produces an actionable
report instead of a chart you have to read by eye.

Supported simulators: **Assetto Corsa**, **Assetto Corsa Competizione**, **iRacing**,
**Le Mans Ultimate** and **RaceRoom**.

---

## What it does

- **Session ingestion** — loads telemetry and setup files, with custom parsers for each
  format.
- **Track normalization** — simulators name circuits differently; Delta unifies them
  against an internal track database.
- **Session analysis** — lap-to-lap comparison, detection of where time is lost, and a
  generated report per session.
- **AI-assisted interpretation** — the Anthropic API translates the numbers into readable
  recommendations, grounded in a domain knowledge base.
- **Teamwork** — user accounts with separate driver, engineer and administrator roles, so
  a race engineer can review the driver's sessions.
- **Asynchronous processing** — heavy analyses run in Celery workers, so uploading a large
  file doesn't block the interface.

## Architecture

```
backend/     FastAPI + SQLAlchemy API, migrations with Alembic
  app/api/         auth · upload · sessions · racing_sessions · analysis · teams · billing · admin
  app/services/    parsers · analysis · tracks · knowledge · ai · reports · storage
  app/tasks/       asynchronous Celery tasks
  tests/           100 tests with pytest
frontend/    Next.js + Tailwind (upload, sessions, comparison, engineer and admin panels)
nginx/       reverse proxy
```

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · Celery · Redis · pandas · numpy ·
Anthropic API · Next.js · TypeScript · Tailwind · Docker Compose · nginx

## Quality

The analysis engine is backed by **100 automated pytest tests**, concentrated where an
error would slip through unnoticed and corrupt the result without failing visibly:

| Suite | Covers |
| --- | --- |
| `test_csv_parser` | reading raw telemetry |
| `test_setup_parser` | interpreting setup files |
| `test_track_normalizer` | track name equivalence across simulators |
| `test_pre_analysis` | data preparation ahead of the analysis |
| `test_session_report` | session report generation |
| `test_kb_service` | the domain knowledge base |

```bash
docker compose exec api pytest
```

## Getting started

Requires Docker and Docker Compose.

```bash
git clone https://github.com/Inf015/Delta.git
cd Delta
cp .env.example .env      # fill in the variables before bringing it up
make up                   # docker compose up -d
make logs                 # follow the logs
```

The API runs at `http://localhost:8000` and the frontend at `http://localhost:3000`.

| Command | Action |
| --- | --- |
| `make up` | brings up all services |
| `make down` | stops them |
| `make build` | rebuilds the images |
| `make logs` | logs from every service |
| `make logs-api` | the API only |
| `make logs-worker` | the Celery worker only |

## Status

Under active development. The core — ingestion, parsers, session analysis and lap
comparison — is working; current work is focused on widening format coverage and sharpening
the setup recommendations.

## Author

**Oliver Infante** — QA Engineer and developer. Sim racing and drag racing with real
telemetry; Delta came out of wanting to apply to the virtual track the same measurement
method I use in the quarter mile.

[Website](https://www.oliver-infante.dev) · [GitHub](https://github.com/Inf015) · [LinkedIn](https://linkedin.com/in/oliver-infante-perez)
