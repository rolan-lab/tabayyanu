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
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
