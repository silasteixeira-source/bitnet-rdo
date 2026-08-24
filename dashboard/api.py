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

    data = {"bitnet": [], "st1": []}

    try:
        # Puxa BITNET
        sheet_bitnet = client.open_by_url(BITNET_URL).worksheet("NOC")
        df_bitnet = pd.DataFrame(sheet_bitnet.get_all_records())
        data["bitnet"] = df_bitnet.to_dict(orient="records")
    except Exception as e:
        print(f"Erro ao ler BITNET: {e}")

    try:
        # Puxa ST1
        sheet_st1 = client.open_by_url(ST1_URL).worksheet("NOC")
        df_st1 = pd.DataFrame(sheet_st1.get_all_records())
        data["st1"] = df_st1.to_dict(orient="records")
    except Exception as e:
        print(f"Erro ao ler ST1: {e}")

    return data

# Serve a interface web na raiz
app.mount("/", StaticFiles(directory="static", html=True), name="static")
