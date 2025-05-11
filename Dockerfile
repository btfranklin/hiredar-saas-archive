# -------- Stage 1: Build front-end assets (Tailwind CSS)
FROM node:20-alpine AS assets
WORKDIR /app

# Install only the packages we need for the CSS build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# Copy Tailwind source and config
COPY tailwind.config.js ./
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

# 3) Disable PDM virtualenv so dependencies install into container Python env
RUN pdm config python.use_venv false

# 4) Install production dependencies via PDM
RUN pdm install --prod

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
CMD ["gunicorn", "hiredar.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"] 