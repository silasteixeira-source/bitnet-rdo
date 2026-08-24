FROM python:3.11-slim

WORKDIR /app

# Copiar dependências Python do Streamlit
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o código do projeto para o container web
COPY . .

# Expor a porta 8501 do Streamlit
EXPOSE 8501

# Comando para rodar o site
CMD ["streamlit", "run", "Validador_Omada_RDO.py", "--server.port=8501", "--server.address=0.0.0.0"]
