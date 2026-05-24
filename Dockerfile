FROM python:3.11-slim

# Instala as dependências de sistema que o Chromium precisa
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    fonts-liberation \
    libfontconfig1 \
    libasound2t64 \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências Python e o Chromium do Playwright
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium

# Copia o código da aplicação
COPY . .

# Inicia o servidor
CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 300
