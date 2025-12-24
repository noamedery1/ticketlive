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
RUN npm run build

# Verify build was created
RUN ls -la dist/ || echo "WARNING: dist directory check"
RUN test -f dist/index.html || (echo "ERROR: Frontend build failed - index.html not found!" && exit 1)

WORKDIR /app

# Environment Settings
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run server only (no scrapers)
CMD python RUN_SERVER_ONLY.py
