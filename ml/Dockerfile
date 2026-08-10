# Multi-stage — ML training / inference image (GPU optional via nvidia runtime)
# Build: docker build -f ml/Dockerfile .
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ml/requirements.txt .
RUN pip install --upgrade pip && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

RUN useradd --create-home --shell /bin/bash mluser
WORKDIR /workspace

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

COPY ml ./ml

USER mluser
CMD ["python", "-m", "ml.training.train_pipeline", "--help"]
