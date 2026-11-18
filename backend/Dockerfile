# ---------------------------------------------------------------------------
# Backend image: FastAPI + PyTorch (CPU only) + Alembic
# Build context: backend/        (see docker-compose.yml)
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# No .pyc files; print logs immediately (no buffering).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) PyTorch from the CPU-only index: ~200 MB instead of ~2.5 GB of CUDA libraries.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision

# 2) Everything else. (torch is already satisfied, so it is not downloaded again.)
#    Copied before the code so this slow layer is cached when only code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# 3) Application code + migrations.
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# 4) Run as an unprivileged user, never as root.
RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/uploads /app/models \
    && chown -R appuser:appuser /app/uploads
USER appuser

EXPOSE 8000

# Apply database migrations, then start the API.
# --proxy-headers + forwarded-allow-ips: trust X-Forwarded-For from Caddy (real client IP
# for rate limiting). Only Caddy can reach this container, so "*" is safe here.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
