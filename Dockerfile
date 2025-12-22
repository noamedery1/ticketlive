FROM python:3.10-slim

# Install Chromium and Driver (Simpler and more stable for Docker)
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl xvfb \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build Frontend
WORKDIR /app/frontend
# Ensure clean install
RUN npm install && npm run build

WORKDIR /app

# Environment Settings
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

CMD python RUN_EVERYTHING.py
