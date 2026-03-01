# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install poetry and the export plugin
RUN pip install --no-cache-dir poetry poetry-plugin-export

COPY pyproject.toml poetry.lock* ./

# Export poetry locked dependencies to standard requirements.txt
RUN poetry export -f requirements.txt --output requirements.txt --without dev

# Create virtualenv and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# ==============================================================================
# Stage 2: Runtime 
# ==============================================================================
FROM python:3.13-slim

WORKDIR /app

# Install runtime package dependencies (libpq required for asyncpg)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* 

# Copy compiled venv from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source code
COPY . .

# Environment configuration
ENV PYTHONPATH=/app
ENV TZ=Asia/Ho_Chi_Minh
ENV PYTHONUNBUFFERED=1

CMD ["python", "scripts/run_scheduler.py"]
