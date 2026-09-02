# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Shared, world-readable browser cache for the simulation agent
    # (agents/simulation_agent.py). It is installed below as root — chromium
    # needs `--with-deps` apt packages — but served at request time by the
    # non-root `appuser` created further down. Without an explicit shared
    # path, `playwright install` defaults to $HOME/.cache/ms-playwright under
    # whichever user ran the install, and appuser's own $HOME would come up
    # empty at runtime: a well-documented Playwright + Docker + non-root gotcha.
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Build deps for psycopg2 / cryptography, removed in the same layer.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Headless-Chromium browser for the simulation agent. `--with-deps` also
# apt-get installs the shared libraries Chromium needs on Debian slim (nss,
# atk, cups, gbm, ...) that this base image doesn't otherwise carry — skip
# that flag and the browser installs but fails to launch at runtime with a
# missing-.so error rather than a clear one. This is the same `playwright
# install chromium` step required once per environment outside Docker too —
# see requirements.txt and agents/simulation_agent.py's module docstring.
# Adds real build time and image size (~400-500MB); the `backend` and `beat`
# services never use it but share this image with `worker`, which does.
RUN playwright install --with-deps chromium

COPY . .

# Run as a non-root user — agents execute model-authored plans, so the blast
# radius of the container itself should be as small as we can make it.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /app "$PLAYWRIGHT_BROWSERS_PATH"
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# app.main:app is the socket.io ASGI wrapper — it serves both HTTP and WS.
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", "--bind", "0.0.0.0:8000", \
     "--timeout", "120", "--access-logfile", "-"]
