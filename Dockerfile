FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libgomp1 provides libgomp.so.1, the OpenMP runtime `implicit` (ALS,
# infrastructure/als_model.py) requires at import time -- without it the
# application fails to start inside this image at all (ApplicationContext
# .create() -> ALS training -> `import implicit.als` ->
# "ImportError: libgomp.so.1: cannot open shared object file"), a real
# container startup failure found and fixed while validating Sprint 34's
# deployment readiness capability against a real build of this image.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8000

# Liveness check against the real GET /health endpoint (Sprint 31), using
# only the stdlib (no curl, avoiding a new system dependency in the image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "readmatch_ai.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
