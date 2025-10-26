FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/data/hf \
    EASYOCR_CACHE_DIR=/data/easyocr \
    # Optional: helps logs/readability if you want to switch later
    OCR_LANGS="ar,en"

WORKDIR /app

# system libs needed by opencv + healthcheck tool
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install -U pip wheel \
 && pip install -r requirements.txt

# OPTIONAL: warm up EasyOCR models for Arabic+English at build time
# (Skip this block if you want a smaller image and don't mind download on first run)
RUN python - <<'PY'
import os
langs = (os.getenv("OCR_LANGS") or "ar,en").split(",")
import easyocr
easyocr.Reader(langs, gpu=False)
PY

COPY app.py /app/app.py

EXPOSE 9001
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=5 \
  CMD curl -fsS http://localhost:9001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9001"]
