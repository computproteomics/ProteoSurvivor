# Data Analysis Game

A browser-based game that teaches data analysis skills.  
Built with **React + Vite** (frontend) and **Django + Django REST Framework** (backend).

---

## Quick Start

### Option A — Docker (recommended)

```bash
cp backend/.env.example backend/.env
docker-compose up --build
```

| Service  | URL                       |
|----------|---------------------------|
| Frontend | http://localhost:3000      |
| Backend  | http://localhost:8000/api  |
| Admin    | http://localhost:8000/admin|

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

---

## Project Structure

```
data-analysis-game/
├── backend/
│   ├── config/          Django settings (base / development / production)
│   ├── api/             API entry-point urls & shared utilities
│   ├── game/            Models (Level, GameSession, Score), views, scoring logic
│   └── data/            Dataset models, synthetic data generators, fixtures
├── frontend/
│   └── src/
│       ├── api/         Axios client
│       ├── components/  GameBoard, DataTable, ChartViewer, Scoreboard, LevelSelector
│       ├── pages/       Home, Game, Results
│       └── store/       Zustand state (gameSlice.js)
├── docker-compose.yml
└── README.md
```

---

## API Endpoints

| Method | Endpoint                       | Description                      |
|--------|-------------------------------|----------------------------------|
| GET    | `/api/levels/`                | List active levels               |
| GET    | `/api/levels/{id}/dataset/`   | Fetch synthetic dataset          |
| POST   | `/api/sessions/`              | Start a new game session         |
| POST   | `/api/sessions/{id}/submit/`  | Submit answer → receive score    |
| GET    | `/api/leaderboard/`           | Top 50 scores                    |

---

## Game Loop

1. Player picks a **level** from the home screen (outlier, correlation, clean, trend).
2. The frontend fetches a **synthetic dataset** from the API and starts a timer.
3. Player examines the data in the **Table** or **Chart** view and selects an answer.
4. On submit the backend **scores** the answer and returns points + feedback.
5. Results page shows the score; the leaderboard updates.

---

## Challenge Types

| Type          | Description                                           |
|---------------|-------------------------------------------------------|
| `outlier`     | Identify rows with anomalous values                   |
| `correlation` | Determine whether two variables are positively/negatively correlated or uncorrelated |
| `clean`       | Flag rows containing invalid / missing data           |
| `trend`       | Classify a time-series as increasing, decreasing, stable, or cyclic |

---

## Tech Stack

| Layer     | Technology                                        |
|-----------|---------------------------------------------------|
| Frontend  | React 18, Vite, React Router 6, Recharts, Zustand |
| Backend   | Django 4.2, Django REST Framework, pandas, numpy, Faker |
| Database  | SQLite (dev) / PostgreSQL (prod)                  |
| Container | Docker + docker-compose                           |
