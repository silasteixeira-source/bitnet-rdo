import os
import json
import math
import datetime
import uuid
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI()

class Agent(BaseModel):
    name: str

class Assignment(BaseModel):
    inep: str
    agent_id: str

class HiddenTicket(BaseModel):
    inep: str

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

def sanitize_data(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    elif isinstance(obj, dict):
        return {k: sanitize_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_data(v) for v in obj]
    return obj

def get_db_path(filename: str) -> str:
    path = f"/app/.streamlit/{filename}"
    if not os.path.exists("/app/.streamlit"):
        path = f"../.streamlit/{filename}"
        if not os.path.exists("../.streamlit"):
            os.makedirs("../.streamlit", exist_ok=True)
    return path

def read_json_db(filename: str, default=None):
    path = get_db_path(filename)
    if not os.path.exists(path):
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default if default is not None else []

def write_json_db(filename: str, data):
    path = get_db_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.get("/api/v1/agents")
def get_agents():
    return read_json_db("agents.json", default=[])

@app.post("/api/v1/agents")
def add_agent(agent: Agent, x_api_key: str = Depends(verify_api_key)):
    agents = read_json_db("agents.json", default=[])
    new_agent = {
        "id": str(uuid.uuid4()),
        "name": agent.name,
        "created_at": datetime.datetime.now().isoformat()
    }
    agents.append(new_agent)
    write_json_db("agents.json", agents)
    return new_agent

@app.delete("/api/v1/agents/{agent_id}")
def delete_agent(agent_id: str, x_api_key: str = Depends(verify_api_key)):
    agents = read_json_db("agents.json", default=[])
    agents = [a for a in agents if a.get("id") != agent_id]
    write_json_db("agents.json", agents)
    return {"status": "ok"}

@app.get("/api/v1/assignments")
def get_assignments():
    return read_json_db("assignments.json", default={})

@app.post("/api/v1/assignments")
def set_assignment(assignment: Assignment, x_api_key: str = Depends(verify_api_key)):
    assignments = read_json_db("assignments.json", default={})
    if not assignment.agent_id:
        if assignment.inep in assignments:
            del assignments[assignment.inep]
    else:
        assignments[assignment.inep] = assignment.agent_id
    write_json_db("assignments.json", assignments)
    return {"status": "ok", "inep": assignment.inep, "agent_id": assignment.agent_id}

@app.get("/api/v1/hidden_tickets")
def get_hidden_tickets():
    hidden = read_json_db("hidden_tickets.json", default={})
    now = datetime.datetime.now()
    valid_hidden = {}
    changed = False
    for inep, ts_str in hidden.items():
        try:
            ts = datetime.datetime.fromisoformat(ts_str)
            if (now - ts).total_seconds() < 86400: # 24 hours
                valid_hidden[inep] = ts_str
            else:
                changed = True
        except:
            changed = True
    
    if changed:
        write_json_db("hidden_tickets.json", valid_hidden)
        
    return valid_hidden

@app.post("/api/v1/hidden_tickets")
def add_hidden_ticket(ticket: HiddenTicket, x_api_key: str = Depends(verify_api_key)):
    hidden = read_json_db("hidden_tickets.json", default={})
    hidden[ticket.inep] = datetime.datetime.now().isoformat()
    write_json_db("hidden_tickets.json", hidden)
    return {"status": "ok", "inep": ticket.inep}

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
        data = sanitize_data(data)
        
        # Injeta o timestamp de modificação do arquivo para o dashboard detectar atrasos
        mtime = os.path.getmtime(snapshot_path)
        data['timestamp'] = datetime.datetime.fromtimestamp(mtime).isoformat()
        
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
