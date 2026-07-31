#!/bin/bash
echo "============================================"
echo "  Omada Cloud Data Exporter"
echo "  Iniciando instalacao das dependencias..."
echo "============================================"
echo ""

# Verificar se Python3 esta instalado
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python3 nao encontrado!"
    echo "Instale Python 3.8+ (sudo apt install python3)"
    exit 1
fi

# Criar virtual environment opcional
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
fi

# Ativar venv e instalar dependencias
source venv/bin/activate 2>/dev/null || true
pip install -r requirements.txt
echo ""

echo "Iniciando o exportador..."
echo ""
python3 omada_exporter.py
