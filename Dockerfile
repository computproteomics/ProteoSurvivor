FROM python:3.11-slim

# Dev container: run Django (8000) + Vite (3000) directly, no nginx.
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor curl gnupg ca-certificates libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (for Vite dev server)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Backend dependencies and source
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/ /app/backend/

# Frontend dependencies and source
COPY frontend/package.json frontend/package-lock.json /app/frontend/
RUN cd /app/frontend && npm ci
COPY frontend/ /app/frontend/

# Provide frontend station config to backend at runtime.
COPY frontend/src/assets/stations.json /app/backend/data/stations.json

# supervisord: start Django and Vite
RUN printf '[supervisord]\n\
    nodaemon=true\n\
    logfile=/dev/null\n\
    logfile_maxbytes=0\n\
    \n\
    [program:django]\n\
    command=sh -c "python manage.py migrate --noinput && if [ -f game/fixtures/leaderboard_seed.json ]; then python manage.py loaddata leaderboard_seed; fi && python manage.py runserver 0.0.0.0:8000"\n\
    directory=/app/backend\n\
    environment=DJANGO_SETTINGS_MODULE="config.settings.development"\n\
    autostart=true\n\
    autorestart=true\n\
    stdout_logfile=/dev/stdout\n\
    stdout_logfile_maxbytes=0\n\
    stderr_logfile=/dev/stderr\n\
    stderr_logfile_maxbytes=0\n\
    \n\
    [program:vite]\n\
    command=npm run dev:frontend -- --host 0.0.0.0 --port 3000\n\
    directory=/app/frontend\n\
    autostart=true\n\
    autorestart=true\n\
    stdout_logfile=/dev/stdout\n\
    stdout_logfile_maxbytes=0\n\
    stderr_logfile=/dev/stderr\n\
    stderr_logfile_maxbytes=0\n' > /etc/supervisor/conf.d/app.conf

EXPOSE 3000 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/app.conf"]
