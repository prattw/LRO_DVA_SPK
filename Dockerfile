# Army Vantage preprocess API — OCR-friendly image (Tesseract included)
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[api]"

# Writable job workspace (mount a volume in production)
ENV VANTAGE_API_HOST=0.0.0.0 \
    VANTAGE_API_PORT=8000 \
    VANTAGE_DATA_DIR=/data

RUN mkdir -p /data \
    && useradd --create-home --uid 1000 appuser \
    && chown appuser:appuser /data

USER appuser
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["python", "-m", "uvicorn", "vantage_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
