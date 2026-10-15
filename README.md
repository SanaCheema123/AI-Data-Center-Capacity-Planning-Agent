# AI Data Center Capacity Planning Agent

Production-oriented capacity planning for GPU, power, storage, and network infrastructure using React, FastAPI, PostgreSQL, Prophet/XGBoost, and LangGraph.

## Important: real-data mode

This project no longer creates synthetic telemetry or demo accounts during normal startup. `python -m app.seed` initializes only reference configuration (roles, forecast model registry, alert thresholds, and scenario templates).

Real infrastructure metrics enter the system through:

- CSV import from **Settings → Data Sources → Import CSV**
- a configured Prometheus source and **Sync**

CSV imports can register previously unseen data centers and GPU clusters, so an empty installation does not depend on seed data.

## Local setup

```powershell
cd backend
python -m pip install -e .
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/register` on a fresh local database. With `BOOTSTRAP_FIRST_USER_AS_ADMIN=true`, the **first registered account becomes Admin** so it can configure real data sources. Later registrations receive Viewer access.

For production set:

```env
BOOTSTRAP_FIRST_USER_AS_ADMIN=false
ALLOW_PUBLIC_REGISTRATION=false
```

and create the first administrator explicitly:

```powershell
python -m app.bootstrap_admin --email ops@company.com --full-name "Ops Lead" --password "YOUR-STRONG-PASSWORD"
```

## Upgrading from an older demo-seeded database

If you already ran a previous build that created `admin@example.com`, `planner@example.com`, or synthetic demo telemetry, remove only those legacy records with:

```powershell
python -m app.purge_demo_data --yes
python -m app.seed
```

Then create your real administrator (or register the first local account) and import/connect real metrics.

## CSV columns

Required (all are needed for the complete GPU/power/storage/network workflow):

`timestamp,data_center,cluster,gpu_utilization,installed_gpus,power_usage_mw,power_capacity_mw,storage_used_tb,storage_capacity_tb,network_throughput_gbps,cooling_power_mw,network_capacity_gbps`

Use ISO-8601 timestamps. Unknown data-center identifiers are registered automatically with neutral metadata (`region/country=unspecified`) and can be enriched later. Rows are rejected when usage exceeds the corresponding physical capacity or when required capacity fields are missing.

## Real-data workflow

After a successful CSV import or Prometheus sync, the backend automatically executes the planning chain for the affected data centers and for the current **All Data Centers** real-data scope:

1. validate and normalize source metrics
2. persist PostgreSQL telemetry with source provenance
3. aggregate capacity-planning features without double-counting repeated samples
4. run GPU, power, storage, and network forecasts using the configured Prophet/XGBoost model
5. calculate utilization, headroom, peak demand, shortage dates, and required expansion
6. refresh scenario results from those persisted forecasts
7. refresh procurement recommendations from capacity gaps
8. evaluate threshold-based shortage alerts
9. expose the same persisted results to LangGraph/AI, reports, and the React dashboard

No synthetic telemetry is created when real data is missing. A missing metric or insufficient history produces an explicit warning/error instead.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The development Compose stack runs migrations plus the safe reference initializer; it does not load synthetic metrics.

## Theme

The product UI uses olive green as the primary infrastructure color and lavender as the AI/forecasting accent. Red/amber/green remain reserved for operational severity and health states.
