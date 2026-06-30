FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/StarGazer1995/stargazing-place-finder"
LABEL org.opencontainers.image.description="Stargazing place finder — light pollution analysis and stargazing location scoring"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies for rasterio/GDAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies via uv
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

EXPOSE 5001

# Gunicorn with Flask app: light_pollution.light_pollution_api:app
CMD [".venv/bin/gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", \
     "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", \
     "light_pollution.light_pollution_api:app"]
