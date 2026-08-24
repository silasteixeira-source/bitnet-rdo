import sys
sys.path.append('dashboard')
from api import get_dashboard_data
import json

try:
    data = get_dashboard_data()
    print("Sucesso! Tipo dos dados:", type(data))
    # Testa se serializa pra JSON sem erro
    json.dumps(data)
    print("JSON OK!")
except Exception as e:
    print("ERRO:", e)
