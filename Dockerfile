# Tabayyanu: one container, data built at image build time from the approved sources.
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Download source data and build the SQLite database, then run the tests:
# a failing check stops the build instead of deploying a broken app.
RUN python scripts/ingest.py && python -m pytest -q tests

ENV PORT=7860
EXPOSE 7860
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s CMD python -c "import urllib.request,os; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT','7860')}/health\")" || exit 1
# --no-access-log: access lines contain client IPs; our logs keep counts and latency only.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
