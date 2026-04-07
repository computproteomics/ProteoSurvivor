# ── Stage 1: Build the React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


# ── Stage 2: Runtime — nginx (frontend) + Django dev server (backend) ────────
FROM python:3.11-slim

# Install nginx and supervisord to run both processes in one container
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx supervisor libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Copy the built React bundle to nginx's web root
COPY --from=frontend-builder /frontend/dist /usr/share/nginx/html

# nginx: serve the React SPA on port 8080 and proxy /api + /admin to Django
RUN printf 'events {}\n\
http {\n\
    include /etc/nginx/mime.types;\n\
    server {\n\
        listen 8080;\n\
        root /usr/share/nginx/html;\n\
        index index.html;\n\
        # React SPA — fall back to index.html for client-side routes\n\
        location / {\n\
            try_files $uri $uri/ /index.html;\n\
        }\n\
        # Proxy API and admin requests to the Django dev server\n\
        location ~ ^/(api|admin)/ {\n\
            proxy_pass http://127.0.0.1:8000;\n\
            proxy_set_header Host localhost;\n\
            proxy_set_header X-Real-IP $remote_addr;\n\
        }\n\
    }\n\
}\n' > /etc/nginx/nginx.conf

# supervisord: start Django then nginx
RUN printf '[supervisord]\n\
nodaemon=true\n\
logfile=/dev/null\n\
logfile_maxbytes=0\n\
\n\
[program:django]\n\
command=sh -c "python manage.py migrate --noinput && python manage.py loaddata data/fixtures/initial_datasets.json && python manage.py runserver 0.0.0.0:8000"\n\
directory=/app\n\
environment=DJANGO_SETTINGS_MODULE="config.settings.development"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
\n\
[program:nginx]\n\
command=nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n' > /etc/supervisor/conf.d/app.conf

EXPOSE 8080

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/app.conf"]
