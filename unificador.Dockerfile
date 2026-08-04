# Dockerfile para o Robô 3: Unificador Automático de Chamados (Omada, OS e RDO -> Google Sheets)
# Imagem leve (sem Chromium), otimizada para VPS (ocupa menos de 100MB de RAM)
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Sao_Paulo

WORKDIR /app

# Instalar pacotes de certificados do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copiar arquivo de dependências e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar os scripts do unificador
COPY unificador_auto.py .
COPY read_excel.py .
COPY utils_omada.py .

# Comando padrão: executa em modo contínuo a cada 300 segundos (5 minutos)
CMD ["python", "-u", "unificador_auto.py", "--intervalo", "300"]
