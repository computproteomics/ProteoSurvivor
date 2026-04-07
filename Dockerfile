# ── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Build a production bundle.  The API client already defaults to the relative
# path "/api", so no VITE_API_URL override is needed.
RUN npm run build


# ── Stage 2: Python / Django runtime ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy the React production bundle into a directory that the combined Django
# settings expose as both a template dir (for index.html) and a static-files
# source (for JS/CSS assets).
COPY --from=frontend-builder /frontend/dist ./frontend_build

# Collect all static assets (including the React bundle) into staticfiles/.
ENV DJANGO_SETTINGS_MODULE=config.settings.combined
RUN python manage.py collectstatic --noinput

COPY backend/startup.sh /startup.sh
RUN chmod +x /startup.sh

EXPOSE 8080

CMD ["/startup.sh"]
