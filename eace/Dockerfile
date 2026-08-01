# Dockerfile para o Robô EACE OS Exporter (RI) em VPS Linux sem interface gráfica (Otimizado para VPS 1GB RAM)
FROM python:3.11-slim

# Variáveis de ambiente para o Chromium Headless
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instalar Chromium, Chromedriver e certificados (sem pacotes legados/descontinuados no Debian 13)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do robô
COPY eace_os_exporter.py .

# Volume persistente para salvar a planilha em dados_eace na VPS
VOLUME ["/app/dados_eace"]

# Comando padrão: executa a cada 3600 segundos (1 hora) por padrão
CMD ["python", "-u", "eace_os_exporter.py", "--intervalo", "3600"]
