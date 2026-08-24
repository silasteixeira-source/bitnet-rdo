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
    import tomllib
    secrets_path = "/app/.streamlit/secrets.toml"
    if not os.path.exists(secrets_path):
        secrets_path = "../.streamlit/secrets.toml" # Para dev local
        
    if os.path.exists(secrets_path):
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
            if "gcp_service_account" in secrets:
                creds = Credentials.from_service_account_info(secrets["gcp_service_account"], scopes=SCOPES)
                return gspread.authorize(creds)
    return None

BITNET_URL = "https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit"
ST1_URL = "https://docs.google.com/spreadsheets/d/1jMc7SW8ECb49j1LP8W879Xz-wyxudkkMYCH9s7nKVdU/edit"

@app.get("/api/data")
def get_dashboard_data():
    client = get_gspread_client()
    if not client:
        return {"error": "Credenciais do Google não encontradas."}

    data = {"bitnet": {}, "st1": {}}

    def fetch_tenant(url, tenant_key):
        try:
            wb = client.open_by_url(url)
            
            # Tenta buscar cada aba e lida graciosamente se estiver vazia ou não existir
            try:
                data[tenant_key]["falta_abrir"] = wb.worksheet("Falta_Abrir_Chamado").get_all_records()
            except:
                data[tenant_key]["falta_abrir"] = []
                
            try:
                data[tenant_key]["abertos"] = wb.worksheet("Chamados_Abertos").get_all_records()
            except:
                data[tenant_key]["abertos"] = []
                
            try:
                data[tenant_key]["fechar"] = wb.worksheet("Fechar_Chamado_Recup").get_all_records()
            except:
                data[tenant_key]["fechar"] = []
                
        except Exception as e:
            print(f"Erro geral ao ler {tenant_key}: {e}")

    fetch_tenant(BITNET_URL, "bitnet")
    fetch_tenant(ST1_URL, "st1")

    return data

# Serve a interface web na raiz
app.mount("/", StaticFiles(directory="static", html=True), name="static")
