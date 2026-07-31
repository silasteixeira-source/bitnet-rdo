@echo off
chcp 65001 >nul
title Omada Cloud Data Exporter
echo ============================================
echo   Omada Cloud Data Exporter
echo   Iniciando instalacao das dependencias...
echo ============================================
echo.

REM Verificar se Python esta instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado!
    echo Instale Python 3.8+ de https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Instalar dependencias
echo Instalando Selenium...
pip install -r requirements.txt
echo.

echo Iniciando o exportador...
echo.
python omada_exporter.py

pause
