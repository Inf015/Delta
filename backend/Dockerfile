FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema (ReportLab necesita libfreetype, pandas necesita gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libfreetype6-dev \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

EXPOSE 8000
