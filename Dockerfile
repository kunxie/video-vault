# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# streaming-form-data ships no Linux arm64 wheel. Build its locked source once,
# then install only the resulting wheel below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

ADD --checksum=sha256:2c5c81fc9c451ea133083bc6da959f87e9b91fba3effe99411f1f90461ea7c5b \
    https://files.pythonhosted.org/packages/dc/fd/d49f3b4e6258e865566fd8aa3da9966f47ca5a7d7fd8ca181f8209010605/streaming_form_data-2.1.0.tar.gz \
    /tmp/streaming_form_data-2.1.0.tar.gz
RUN --mount=type=cache,target=/root/.cache/uv \
    uv build --wheel /tmp/streaming_form_data-2.1.0.tar.gz --out-dir /wheels

# Install runtime dependencies first, cached separately from app source.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-build \
        --no-install-package streaming-form-data \
    && uv pip install --python .venv/bin/python --no-index --no-deps --no-build \
        --find-links /wheels streaming-form-data==2.1.0

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini


FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

# Migrations run as the platform migration image via a command override:
#   alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
