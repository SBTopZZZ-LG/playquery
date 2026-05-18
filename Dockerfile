FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install the shared libraries Chromium needs at runtime inside the container.
# Patchright launches the browser in headless mode, but Chromium still depends
# on these graphics, font, accessibility, and TLS/system integration packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
  ca-certificates \
  fonts-liberation \
  libasound2 \
  libatk-bridge2.0-0 \
  libatk1.0-0 \
  libcups2 \
  libdbus-1-3 \
  libdrm2 \
  libgbm1 \
  libglib2.0-0 \
  libgtk-3-0 \
  libnspr4 \
  libnss3 \
  libpango-1.0-0 \
  libx11-6 \
  libx11-xcb1 \
  libxcb1 \
  libxcomposite1 \
  libxdamage1 \
  libxext6 \
  libxfixes3 \
  libxkbcommon0 \
  libxrandr2 \
  xdg-utils \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN apt-get update && apt-get install -y --no-install-recommends \
  git \
  && pip install --upgrade pip \
  && pip install -r requirements.txt \
  && python -m patchright install chromium \
  && apt-get purge -y --auto-remove git \
  && rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
