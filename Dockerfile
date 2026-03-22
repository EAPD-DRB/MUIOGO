FROM python:3.11-slim

# App config
ARG PORT=5002
ENV PORT=${PORT} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create non-root user
RUN useradd -m muiogo

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        glpk-utils coinor-cbc unzip && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY --chown=muiogo:muiogo . .

# Seed demo data and fix permissions
RUN chown -R muiogo:muiogo /app/WebAPP/DataStorage

EXPOSE ${PORT}

# Basic healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}')" \
    || exit 1

USER muiogo

WORKDIR /app/API

CMD ["sh", "-c", "python -m waitress --host=0.0.0.0 --port=${PORT} app:app"]
