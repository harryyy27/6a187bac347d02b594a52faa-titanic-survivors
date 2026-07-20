# Production image for the Titanic Survivors API.
FROM python:3.11-slim

WORKDIR /app

ENV POETRY_HOME=/opt/poetry \
    PATH="/opt/poetry/bin:${PATH}"

RUN pip install --no-cache-dir poetry

# Copy only the dependency manifests first so the dependency-install layer
# stays cached across source-only changes.
COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --without dev

# Copy the remaining application source.
COPY app ./app
COPY models ./models

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
