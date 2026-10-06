# AGENTS.md

## Project

ProteoSurvivor: a browser-based proteomics education game. Players configure lab
workflow stations (sample prep → mass spec → spectral search → stats → final report).
**React + Vite** frontend, **Django + DRF** backend, SQLite dev / PostgreSQL prod.

## Quick Start (Manual)

```bash
cd frontend
npm install    # also bootstraps backend/venv if missing
npm run dev    # starts Vite (port 3000) + Django (port 8000) concurrently
```

## Quick Start (Docker)

```bash
cp backend/.env.example backend/.env
docker build -t proteosurvivor .
docker run --env-file backend/.env -p 3000:3000 proteosurvivor
```

## Commands

| Task | Command | Notes |
|------|---------|-------|
| Frontend lint | `cd frontend && npm run lint` | ESLint on `src/` |
| Frontend build | `cd frontend && npm run build` | Vite production build |
| Backend tests | `cd backend && python manage.py test game.tests --verbosity=2` | Requires `DJANGO_SETTINGS_MODULE=config.settings.development` |
| Backend migrate | `cd backend && venv/bin/python manage.py migrate` | SQLite by default |

**No backend lint or typecheck is configured.** CI only runs backend tests.

## Architecture

### Frontend (`frontend/`)

- **Framework**: React 18, React Router 6, Zustand state, Axios HTTP client
- **Entry**: `src/App.jsx` — routes with `RequireAuth` guard (userId from Zustand)
- **State**: `src/store/gameSlice.js` (single Zustand store)
- **HTTP**: `src/api/client.js` — Axios instance, CSRF cookie interceptor, base URL from `VITE_API_URL` or `BASE_URL + 'api'`
- **Station config**: `src/assets/stations.json` — read by both frontend and backend
- **Vite config**: `vite.config.js` — `VITE_BASE_PATH` env var sets sub-path for production (`/ProteoSurvivor/`), proxy rewrites strip it before hitting Django

### Backend (`backend/`)

- **Framework**: Django 6.1 + DRF
- **Settings split**: `config/settings/base.py`, `development.py`, `production.py`
- **Single app**: `game/` — models, views, serializers, station simulators in `services.py`
- **Data dir**: `backend/data/` — `ParameterTable.csv` + `ParameterSet_*.tsv` reference datasets
- **Session-based dataset passing**: DataFrame serialized into Django session via `DataFrameSessionSerializer`
- **Station config**: Backend reads `frontend/src/assets/stations.json` at startup via `STATIONS_CONFIG`

### Data flow

1. Frontend POSTs params to `/api/stations/<station_id>/run/`
2. Backend `run_station_view` dispatches to `_simulate_<station>()` in `services.py`
3. Each simulator receives the current DataFrame (from session) + params, returns result dict with `dataset`, `success`, `score`, `feedback`, optional plots
4. Result dataset is serialized back into session for the next station

### Station pipeline order

`sample_prep → mass_spec → spectral_search → transform → filtering → normalize → imputer → statistical_analysis → multiple_testing_corrector → the_cutter → final_report`

Entry guard: `mass_spec` requires `sample_prep` to have run first.

## Testing

- **Backend only** — no frontend tests exist
- Tests use `unittest.mock.patch` to stub plotting functions and `pd.read_csv`
- `_make_dataset()` and `_make_dataset_with_stats()` helpers create minimal proteomics DataFrames
- Station config coverage tests iterate parameter combos from `stations.json` (capped at 10)
- CI: GitHub Actions runs `backend-tests.yml` on PRs and pushes to main (Python 3.13)

## Gotchas

- `npm run dev` from `frontend/` auto-bootstraps `backend/venv/` and runs migrations — no manual pip install needed
- `VITE_BASE_PATH` must be set for production builds; dev server defaults to `/`
- CSRF token is read from cookie (not header) by the Axios interceptor in `client.js`
- `stations.json` is the single source of truth for station parameter options, shared between frontend and backend
- `backend/data/` contains ~570 `ParameterSet_*.tsv` files used by spectral search simulation
- Django settings module must be set explicitly: `DJANGO_SETTINGS_MODULE=config.settings.development`
