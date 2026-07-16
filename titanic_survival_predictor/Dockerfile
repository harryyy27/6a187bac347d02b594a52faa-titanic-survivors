# Production Dockerfile for titanic_survival_predictor
#
# This component is a batch ML training/inference pipeline (Kaggle-style:
# load -> clean -> engineer features -> train an XGBoost ensemble -> predict
# -> write submission.csv), not a request/response web service. There is no
# HTTP API in the source, so there is no gunicorn/nginx process to front --
# the "production server" for this workload is the single production
# pipeline process itself, run to completion as the container's main
# process (the batch-job equivalent of a production server process).
FROM python:3.11-slim

WORKDIR /app

# Validate the dependency manifest before installing anything from it.
COPY requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && pip install --dry-run --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

# Copy all source code for the component.
COPY titanic.py ./titanic.py
COPY Titanic.ipynb ./Titanic.ipynb

ENV PYTHONUNBUFFERED=1

# Runs the full production pipeline (self-contained production entrypoint).
CMD ["python", "titanic.py"]
