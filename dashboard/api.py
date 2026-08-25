import os
import json
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

NOC_API_KEY = os.getenv("NOC_API_KEY", "secret123")

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != NOC_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized API Key")
    return x_api_key

@app.get("/api/v1/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/v1/dashboard")
def get_dashboard_data(tenant: str, x_api_key: str = Depends(verify_api_key)):
    snapshot_path = f"/app/.streamlit/snapshots/{tenant}.json"
    if not os.path.exists(snapshot_path):
        # Fallback para ambiente local de dev
        snapshot_path = f"../.streamlit/snapshots/{tenant}.json"
        
    if not os.path.exists(snapshot_path):
        return {"error": f"Snapshot JSON não encontrado para o tenant '{tenant}'. O pipeline ainda está processando."}
        
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        return {"error": f"Erro ao ler snapshot local: {e}"}

@app.get("/")
def serve_index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("{{ NOC_API_KEY }}", NOC_API_KEY)
    return HTMLResponse(content=content)

# Serve a interface web (app.js, style.css, imagens)
app.mount("/", StaticFiles(directory="static"), name="static")
