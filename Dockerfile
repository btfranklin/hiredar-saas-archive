# -------- Stage 1: Build front-end assets (Tailwind CSS)
FROM node:20-alpine AS assets
WORKDIR /app

# Install all deps (including dev) so Tailwind CLI is present
COPY package.json package-lock.json ./
RUN npm ci

# Copy Tailwind source and config
COPY tailwind.config.js ./

# ------------------------------------------------------------------
#  IMPORTANT:  Provide Tailwind with the files it must scan so that
#  utility classes we actually use (e.g. flex, grid, gap-*) make it
#  through purge.  They live in the Django template directories, so
#  copy them _before_ invoking the CLI.  (Only lightweight text files
#  are added, so the image size doesn't increase meaningfully.)
# ------------------------------------------------------------------
COPY apps ./apps               # Django apps – templates under apps/**/templates/
COPY templates ./templates     # Project-level templates (if any)
COPY static/js ./static/js     # HTMX/Alpine or other scripts that add classes

COPY assets ./assets

# Build the minified CSS file
RUN npx tailwindcss -i ./assets/css/tailwind.css -o ./static/css/tailwind.css --minify


# -------- Stage 2: Python / Django runtime
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# System packages required by psycopg and Pillow
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ----------------------------------------------------------------------------
# Dependency installation via PDM
# ----------------------------------------------------------------------------
# 1) Install PDM (lightweight Python package/dependency manager)
RUN pip install --upgrade pip pdm

# 2) Copy only the lockfile and project metadata first so Docker layer caching
#    can be leveraged when application code changes but deps remain the same.
COPY pyproject.toml pdm.lock ./

# 3) Export production dependencies to a requirements file and install them
RUN pdm export --prod --without-hashes -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# ----------------------------------------------------------------------------
# Copy application source and pre-built assets
# ----------------------------------------------------------------------------
COPY . /app/

# Copy the compiled CSS from the assets stage into the correct location
COPY --from=assets /app/static/css/tailwind.css /app/static/css/tailwind.css

# Collect static files (they will be served by Whitenoise)
RUN python manage.py collectstatic --noinput

# Expose the port Sevalla provides via $PORT
EXPOSE 8000

# Default command (can be overridden by Sevalla process definition)
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn hiredar.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2"] 