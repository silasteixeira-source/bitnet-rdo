FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependências da API (FastAPI, Pandas, etc)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do backend
COPY api.py .

# Copiar frontend (HTML, CSS, JS) para a pasta estática
COPY static/ ./static/

# O container vai rodar a porta 8080 internamente
EXPOSE 8080

# Comando para iniciar o servidor Uvicorn
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
