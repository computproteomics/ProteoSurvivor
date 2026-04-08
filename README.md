# ProteoSurviver

A browser-based proteomics education game where players step into the role of a
computational proteomics researcher.  
Guide samples through a full lab workflow — from sample preparation through mass
spectrometry, database search, and data analysis — then report your findings to
your supervisor Veit.

Built with **React + Vite** (frontend) and **Django + Django REST Framework** (backend).

---

## Quick Start

### Option A — Docker (recommended)

The repository ships with a single multi-stage `Dockerfile` that builds the
React bundle and serves it via **nginx** on port **8080**, proxying API and admin
requests to the Django backend running on port 8000 inside the same container.

```bash
cp backend/.env.example backend/.env   # set SECRET_KEY at minimum
docker build -t proteosurvivor .
docker run --env-file backend/.env -p 8080:8080 proteosurvivor
```

| Service  | URL                        |
|----------|----------------------------|
| App      | http://localhost:8080       |
| API      | http://localhost:8080/api   |
| Admin    | http://localhost:8080/admin |

---

### Option B — Manual

#### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # edit SECRET_KEY and DB settings
python manage.py migrate
python manage.py loaddata data/fixtures/initial_datasets.json
python manage.py runserver
```

#### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_URL=http://localhost:8000/api
npm run dev
```

The frontend dev server starts on **http://localhost:5173**.

---

## Project Structure

```
ProteoSurviver/
├── backend/
│   ├── config/          Django settings (base / development / production)
│   ├── api/             API entry-point urls & shared utilities
│   ├── game/            Models (Level, GameSession, StationRun, Score), views, services
│   └── data/            Synthetic dataset generators, fixtures
├── frontend/
│   └── src/
│       ├── api/         Axios client (station & game endpoints)
│       ├── screens/     Intro, WorldMap, StationView, ParametrizationView, StationResults
│       └── store/       Zustand state (gameSlice.js)
└── Dockerfile
```

---

## API Endpoints

| Method | Endpoint                          | Description                               |
|--------|-----------------------------------|-------------------------------------------|
| POST   | `/api/stations/{id}/run/`         | Run a proteomics station with parameters  |
| GET    | `/api/levels/`                    | List active challenge levels              |
| GET    | `/api/levels/{id}/dataset/`       | Fetch a synthetic dataset for a level     |
| POST   | `/api/sessions/`                  | Start a new game session                  |
| POST   | `/api/sessions/{id}/submit/`      | Submit an answer → receive score          |
| GET    | `/api/leaderboard/`               | Top 50 scores                             |

---

## Game Flow

1. The **Intro** screen introduces the scenario: an infected cell sample needs to
   be analysed.
2. The **World Map** lists the five lab stations. Completed stations are marked ✅.
3. The player clicks a station to read its **description** and **objective**.
4. Clicking *Configure & Run* opens the **Parametrization** screen where
   station-specific settings are chosen (enzyme, acquisition mode, FDR threshold,
   etc.).
5. Parameters are sent to the backend which **simulates** realistic lab results.
6. The **Results** screen shows a summary, key metrics, and a recommendation.
7. The player confirms results and returns to the World Map to continue.
8. After completing all stations the player writes a report in the **Veit**
   station, which evaluates the quality of the findings and closes the experiment.

---

## Lab Stations

| Station ID      | Name                | Description                                              |
|-----------------|---------------------|----------------------------------------------------------|
| `sample_prep`   | Sample Preparation  | Lysis, reduction, alkylation, and tryptic digestion      |
| `mass_spec`     | Mass Spectrometer   | DDA / DIA acquisition with configurable gradient & resolution |
| `search_setup`  | Search Engine Setup | Database search with enzyme, missed cleavages, and FDR   |
| `data_analysis` | Data Analysis       | Normalisation, statistical testing, fold-change analysis |
| `veit`          | Veit                | Supervisor who reviews the final written report          |

---

## Tech Stack

| Layer     | Technology                                              |
|-----------|---------------------------------------------------------|
| Frontend  | React 18, Vite, React Router 6, Recharts, Zustand, Axios |
| Backend   | Django 4.2, Django REST Framework, pandas, numpy, Faker  |
| Database  | SQLite (dev) / PostgreSQL (prod)                        |
| Container | Docker (single multi-stage image, nginx + supervisord)  |
