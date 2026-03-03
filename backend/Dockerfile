# Use an official Python runtime as a parent image
FROM python:3.12-slim as base

# Prevent Python from writing pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install runtime dependencies (no build-essential overhead)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq5 \
       curl \
       sed \
       postgresql-client \
       redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . .

# Make scripts executable
RUN chmod +x /app/start.py

# --- Target: API ---
FROM base as api
COPY requirements-common.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt
EXPOSE 8000
CMD ["python", "/app/start.py"]

# --- Target: Worker ---
FROM base as worker
COPY requirements-common.txt requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-worker.txt

# --- Target: Flower ---
FROM base as flower
COPY requirements-common.txt requirements-flower.txt ./
RUN pip install --no-cache-dir -r requirements-flower.txt
