# Reproducible environment for green-tapper (Python 3.12).
# The adb CLIENT is the pure-python `adbutils` dependency, so NO adb binary is
# needed in the image — it talks over TCP to the adb SERVER on the host. The
# application code is mounted at run time, so editing code never triggers a rebuild.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.5.1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Only the dependency manifest is copied, so this layer is cached until the
# dependencies (not the code) actually change.
COPY pyproject.toml poetry.lock* ./

# libglib2.0-0 -> required by opencv-python-headless (libgthread).
# --only main  -> install runtime deps only (no dev group); with package-mode =
#                 false there is no root package, so the mounted source stays the
#                 single source of truth.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install "poetry==${POETRY_VERSION}" \
    && poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction

ENTRYPOINT ["python", "src/main.py"]
