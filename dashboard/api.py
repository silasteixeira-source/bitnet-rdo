import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client():
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib
        
    secrets_path = "/app/.streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        secrets_path = "../.streamlit/secrets.toml" # Para dev local
        
    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, "rb") as f:
                secrets = tomllib.load(f)
                if "gcp_service_account" in secrets:
                    creds = Credentials.from_service_account_info(secrets["gcp_service_account"], scopes=SCOPES)
                    return gspread.authorize(creds)
    except Exception as e:
        print(f"Erro ao autenticar: {e}")
        
    return None

BITNET_URL = "https://docs.google.com/spreadsheets/d/167LUrFFBJBlQ-Jh7cX717r32F2c8tfq1zsx_0FIC0WY/edit"
ST1_URL = "https://docs.google.com/spreadsheets/d/1jMc7SW8ECb49j1LP8W879Xz-wyxudkkMYCH9s7nKVdU/edit"

import time
API_CACHE = {
    "data": None,
    "last_fetch": 0
}

@app.get("/api/data")
def get_dashboard_data():
    global API_CACHE
    now = time.time()
    
    # Se o último fetch foi há menos de 15 segundos, retorna o cache da memória RAM
    if API_CACHE["data"] and (now - API_CACHE["last_fetch"] < 15):
        return API_CACHE["data"]

    client = get_gspread_client()
    if not client:
        return {"error": "Credenciais do Google não encontradas."}

    data = {"bitnet": {}, "st1": {}}

    def fetch_tenant(url, tenant_key):
        wb = client.open_by_url(url)
        for ws_name, dict_key in [("Falta_Abrir_Chamado", "falta_abrir"), 
                                  ("Chamados_Abertos", "abertos"), 
                                  ("Fechar_Chamado_Recup", "fechar")]:
            try:
                data[tenant_key][dict_key] = wb.worksheet(ws_name).get_all_records()
            except gspread.exceptions.WorksheetNotFound:
                data[tenant_key][dict_key] = []

    try:
        fetch_tenant(BITNET_URL, "bitnet")
        fetch_tenant(ST1_URL, "st1")
    except Exception as e:
        return {"error": f"Erro de API do Google: {str(e)}"}

    # Salva no cache
    if data["bitnet"] and data["st1"]:
        API_CACHE["data"] = data
        API_CACHE["last_fetch"] = now

    return data

# Serve a interface web na raiz
app.mount("/", StaticFiles(directory="static", html=True), name="static")
