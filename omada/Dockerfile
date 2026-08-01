FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    wget \
    curl \
    unzip \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/dados_omada && chmod -R 777 /app/dados_omada

ENV OMADA_CLI=true
ENV OMADA_INTERVAL=30
ENV OMADA_DIR=/app/dados_omada

CMD ["python", "omada_exporter_cli.py", "--cli"]
