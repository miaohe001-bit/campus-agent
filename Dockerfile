FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml ./
COPY backend/scripts ./scripts
RUN pip install --no-cache-dir ".[dev]"

COPY backend/app ./app
COPY backend/tests ./tests
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
