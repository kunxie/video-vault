# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=python:3.12.13-slim-bookworm@sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.11.28@sha256:0f36cb9361a3346885ca3677e3767016687b5a170c1a6b88465ec14aefec90aa

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY --from=uv /uv /uvx /bin/

# streaming-form-data ships no Linux ARM64 wheel. Build its locked source once,
# then install only the resulting wheel below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

ADD --checksum=sha256:2c5c81fc9c451ea133083bc6da959f87e9b91fba3effe99411f1f90461ea7c5b \
    https://files.pythonhosted.org/packages/dc/fd/d49f3b4e6258e865566fd8aa3da9966f47ca5a7d7fd8ca181f8209010605/streaming_form_data-2.1.0.tar.gz \
    /tmp/streaming_form_data-2.1.0.tar.gz
RUN --mount=type=cache,target=/root/.cache/uv \
    uv build --wheel /tmp/streaming_form_data-2.1.0.tar.gz --out-dir /wheels

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-build \
        --no-install-package streaming-form-data \
    && uv pip install --python .venv/bin/python --no-index --no-deps --no-build \
        --find-links /wheels streaming-form-data==2.1.0

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini


FROM ${PYTHON_IMAGE} AS runtime

ARG SOURCE_URL=https://github.com/kunxie/video-vault
ARG APP_VERSION=0.0.0
ARG VCS_REF=uncommitted
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="video-vault" \
      org.opencontainers.image.description="Personal MP4 storage and playback service" \
      org.opencontainers.image.source="${SOURCE_URL}" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}"

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIDEO_VAULT_BUILD_REVISION="${VCS_REF}" \
    VIDEO_VAULT_VERSION="${APP_VERSION}"

RUN groupadd --system --gid 10001 vault \
    && useradd --system --uid 10001 --gid vault --no-create-home \
        --home-dir /nonexistent --shell /usr/sbin/nologin vault

WORKDIR /app
COPY --from=builder --chown=10001:10001 /app /app

USER 10001:10001
EXPOSE 8000
STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "-m", "app.cli"]
CMD ["serve"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
