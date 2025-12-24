FROM python:3.10-slim

# Install curl and Node.js (Version 20) - Only needed for frontend build
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages (minimal - no selenium/chromedriver needed)
COPY requirements_server.txt .
RUN pip install --no-cache-dir -r requirements_server.txt || pip install --no-cache-dir fastapi uvicorn[standard]

# Copy all files
COPY . .

# Build Frontend
WORKDIR /app/frontend
RUN npm install --legacy-peer-deps || npm install

# Run build with verbose output
RUN npm run build 2>&1

# Debug: Show what was actually built
RUN echo "=== Current directory ===" && pwd && \
    echo "=== All files in frontend/ ===" && ls -la && \
    echo "=== dist/ directory contents ===" && \
    (ls -la dist/ 2>&1 || echo "dist/ directory does not exist!") && \
    echo "=== Checking for index.html ===" && \
    (test -f dist/index.html && echo "✓ index.html found" || (echo "✗ index.html NOT FOUND!" && ls -la dist/ && exit 1)) && \
    echo "=== Checking for assets ===" && \
    (test -d dist/assets && echo "✓ assets directory found" && ls -la dist/assets/ || echo "⚠ assets directory not found")

WORKDIR /app

# Environment Settings
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run server only (no scrapers)
CMD python RUN_SERVER_ONLY.py
