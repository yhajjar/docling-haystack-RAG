FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/data/hf

WORKDIR /app
COPY requirements.txt /app/
RUN apt-get update && apt-get install -y --no-install-recommends \
      git build-essential curl \
    && pip install -U pip wheel \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /app/app.py
EXPOSE 9001
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=5 \
  CMD curl -fsS http://localhost:9001/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "9001"]
