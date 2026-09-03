FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY scripts ./scripts
RUN pip install --no-cache-dir ".[dev]"

COPY app ./app
COPY tests ./tests
COPY alembic.ini ./
COPY alembic ./alembic

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
