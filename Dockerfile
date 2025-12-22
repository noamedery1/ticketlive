FROM python:3.10-slim

# Install Chromium, Driver, AND Node.js prereqs
RUN apt-get update && apt-get install -y \
    wget gnupg unzip curl xvfb \
    chromium \
    chromium-driver \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (Version 20)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build Frontend
WORKDIR /app/frontend
RUN npm install && npm run build

WORKDIR /app

# Environment Settings
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

CMD python RUN_EVERYTHING.py
