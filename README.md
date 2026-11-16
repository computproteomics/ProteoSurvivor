# ProteoSurvivor

A browser-based proteomics education game where players step into the role of a
computational proteomics researcher.
Navigate a 2D lab map, visit stations in any order, configure each step of the
workflow — from sample preparation through mass spectrometry, database search,
and statistical analysis — then hand in your report to your supervisor.

Find the running version ![here](computproteomics.bmb.sdu.dk/ProteoSurvivor)

Built with **React + Vite** (frontend) and **Django + Django REST Framework** (backend).

---

## Quick Start

### Option A — Docker (recommended)

The repository ships with a single `Dockerfile` that builds the React bundle and
serves it via **Vite** on port **3000**, proxying API and admin requests to the
Django backend running on port **8000** inside the same container.

The app is deployed at `/ProteoSurvivor/` by default (matching
`https://computproteomics.bmb.sdu.dk/ProteoSurvivor/`).

```bash
cp backend/.env.example backend/.env   # set SECRET_KEY at minimum
docker build -t proteosurvivor .
docker run --env-file backend/.env -p 3000:3000 proteosurvivor
```

#### Persisting the database outside the container

By default the SQLite database lives at `/app/backend/db.sqlite3` inside the
container and is lost when the container is removed. To keep it outside the
container, bind-mount the database file from the host:

```bash
# Create the file first so Docker binds a file, not a directory
touch /path/on/host/db.sqlite3

docker run --env-file backend/.env \
    -p 3000:3000 \
    -v /path/on/host/db.sqlite3:/app/backend/db.sqlite3 \
    proteosurvivor
```

When you restart the container with the same bind mount, Docker reuses the
existing host file instead of overwriting it. Startup steps such as Django's
`migrate` command can still update the mounted database in place.

#### Purging (resetting) the database

To wipe all data and start fresh, stop the container and delete the mounted
database file:

```bash
rm /path/on/host/db.sqlite3
```

The next time the container starts, Django's `migrate` step re-creates an
empty database automatically.

---

The nginx `location` block that proxies to the container:

```nginx
location /ProteoSurvivor/ {
    proxy_pass http://127.0.0.1:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

### Option B — Manual

#### Run Both
`npm run dev` starts both the Vite dev server and the Django backend. `npm install`
in `frontend/` now also bootstraps the Python virtual environment
(`backend/venv/`) if it does not exist, so no manual `pip install` is needed.

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

The frontend dev server starts on **http://localhost:3000**.

### Generate a game report

The Django management command reads the active database and writes a report with
CSV summaries, PNG and SVG figures, `summary.md`, and `summary.html`.

From the repository root, using the usual development database:

```bash
backend/venv/bin/python backend/manage.py generate_game_report \
    --output-dir reports/game_report
```

The development database defaults to `backend/db.sqlite3`. To analyse a copied
database in the repository root, set `SQLITE_DB_PATH` to its path relative to
the `backend/` directory:

```bash
SQLITE_DB_PATH=../db.sqlite3 \
backend/venv/bin/python backend/manage.py generate_game_report \
    --output-dir reports/game_report
```

The report excludes seed accounts whose usernames start with `seed_player_`,
retains duplicate and retry runs, and excludes anonymous runs by default. Add
`--include-anonymous` to include runs without a player account.

Open `reports/game_report/summary.html` in a browser, or use
`reports/game_report/summary.md` in a Markdown viewer. The output also includes
`participant_key.csv`, which maps the generic participant IDs shown in the
figures to their database accounts.


### Recalculate scores after updating

If you update to a new version of the game or apply some local changes,
you can use the following command to recalculate the existing scores in the leaderboard:

```bash
backend/venv/bin/python backend/manage.py recalculate
```
This will "replay" all existing user actions and show you a summary of changes.
They will only be committed after your confirmation. For safety, if any errors happen during
the recalculation, or if runs previously marked as successful fail,
the results will not be overwritten.

**Note:** if recalculating results from before #133 was merged, consider adding `--skip-repeated-runs`.
"Repeated runs" refers to consecutive runs of the same station. Prior to that PR, runs were still saved
to the database if the user clicked "Adjust parameters" to effectively start over, so this key is necessary
to avoid reapplying the same operations to the dataset.

---

## Project Structure

```
ProteoSurvivor/
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
8. After completing all stations the player hands in their report at **The "Please Let This Be Significant" Lounge**
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
| `final_report`              | The "Please Let This Be Significant" Lounge | Final report station for high-stakes interpretation and submission |

---

## Tech Stack

| Layer     | Technology                                              |
|-----------|---------------------------------------------------------|
| Frontend  | React 18, Vite, React Router 6, Recharts, Zustand, Axios |
| Backend   | Django 6.1, Django REST Framework, pandas, numpy, Faker  |
| Database  | SQLite (dev) / PostgreSQL (prod)                        |
| Container | Docker (single multi-stage image, nginx + supervisord)  |
