FROM python:3.10-slim
RUN apt-get update && apt-get install -y wget gnupg unzip curl xvfb && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /etc/apt/keyrings && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub > /etc/apt/keyrings/google.pub
RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google.pub] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
RUN apt-get update && apt-get install -y google-chrome-stable
RUN curl -fsSL [https://deb.nodesource.com/setup_20.x](https://deb.nodesource.com/setup_20.x) | bash - && apt-get install -y nodejs
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
WORKDIR /app/frontend
RUN npm install && npm run build
WORKDIR /app
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1
CMD python RUN_EVERYTHING.py