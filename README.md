# ProteoSurviver

A browser-based proteomics education game where players step into the role of a
computational proteomics researcher.  
Navigate a 2D lab map, visit stations in any order, configure each step of the
workflow — from sample preparation through mass spectrometry, database search,
and statistical analysis — then hand in your report to your supervisor.

Built with **React + Vite** (frontend) and **Django + Django REST Framework** (backend).

---

## Quick Start

### Option A — Docker (recommended)

The repository ships with a single `Dockerfile` that builds the React bundle and
serves it via **Vite** on port **3000**, proxying API and admin requests to the
Django backend running on port **8000** inside the same container.

The app is deployed at `/ProteoSurviver/` by default (matching
`https://computproteomics.bmb.sdu.dk/ProteoSurviver/`).

```bash
cp backend/.env.example backend/.env   # set SECRET_KEY at minimum
docker build -t proteosurvivor .
docker run --env-file backend/.env -p 3000:3000 proteosurvivor
```

The nginx `location` block that proxies to the container:

```nginx
location /ProteoSurviver/ {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

### Option B — Manual

#### Run Both
`npm run dev` starts both the Vite dev server and the Django backend. On first
run it creates a Python virtual environment (`backend/venv/`) automatically, so
no manual `pip install` is needed.

##### First time
```bash
cd frontend
npm install
npm run dev
```

##### If all installed

```bash
cd frontend
npm run dev
```

#### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # edit SECRET_KEY and DB settings
python manage.py migrate
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
│   ├── game/            Model (StationRun), views, serializers, station simulators
│   └── data/            Reference datasets (e.g. ParameterSet_001.tsv)
├── frontend/
│   └── src/
│       ├── api/         Axios client (client.js)
│       ├── assets/      Station config (stations.json, stationConfig.js)
│       ├── screens/     Intro, WorldMap, MapSetup, StationView,
│       │                ParametrizationView, StationResults
│       ├── store/       Zustand state (gameSlice.js)
│       └── styles/      Global CSS
└── Dockerfile
```

---

## API Endpoints

| Method | Endpoint                            | Description                              |
|--------|-------------------------------------|------------------------------------------|
| POST   | `/api/stations/<station_id>/run/`   | Run a proteomics station with parameters |

---

## Game Flow

1. The **Intro** screen introduces the scenario: an infected cell sample needs to
   be analysed.
2. The **World Map** shows a 2D canvas lab with a player character the user can
   move using arrow keys or WASD.  Station tiles are highlighted; completed
   stations display a green "OK" badge.
3. The player walks up to (or clicks) a station tile to open the **Station** screen
   with a description and objective.
4. Clicking *Configure & Run* opens the **Parametrization** screen where
   station-specific settings are chosen (enzyme, acquisition mode, FDR threshold,
   etc.).
5. Parameters are sent to the backend which **simulates** realistic lab results.
6. The **Results** screen shows a summary, key metrics, and a recommendation.
7. The player confirms results and returns to the World Map to continue.
8. After completing all stations the player hands in their report at the **Veit**
   station, which evaluates the quality of the findings and closes the experiment.

---

## Lab Stations

Station definitions live in `frontend/src/assets/stations.json`; the backend
reads the same file at startup via `STATIONS_CONFIG`.

| Station ID                  | Name                        | Description                                                       |
|-----------------------------|-----------------------------|-------------------------------------------------------------------|
| `sample_prep`               | Sample Preparation          | Prepare infected and control samples for mass spectrometry        |
| `mass_spec`                 | Mass Spectrometer           | Run samples on the mass spectrometer (DDA acquisition)            |
| `spectral_search`           | Spectral Search Station     | Match spectra against a protein sequence database                 |
| `filtering`                 | Filtering Station           | Remove low-confidence identifications and contaminants            |
| `transform`                 | Transform Station           | Log-transform intensity values to stabilize variance              |
| `normalize`                 | Normalize Station           | Correct systematic intensity shifts between samples               |
| `imputer`                   | Imputer Station             | Handle missing values from low abundance / stochastic sampling    |
| `multiple_testing_corrector`| Multiple Testing Corrector  | Control false discoveries across many statistical tests           |
| `the_cutter`                | The Cutter                  | Set fold-change and FDR cutoffs for the final candidate list      |
| `statistical_analysis`      | Statistical Analysis        | Compare conditions and identify significantly regulated proteins  |
| `veit`                      | Veit                        | Supervisor who reviews the final written report                   |

---

## Tech Stack

| Layer     | Technology                                              |
|-----------|---------------------------------------------------------|
| Frontend  | React 18, Vite, React Router 6, Recharts, Zustand, Axios |
| Backend   | Django 4.2, Django REST Framework, pandas, numpy, Faker  |
| Database  | SQLite (dev) / PostgreSQL (prod)                        |
| Container | Docker (single multi-stage image, nginx + supervisord)  |
