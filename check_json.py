import os
import json

path = os.path.join(".streamlit", "snapshots", "bitnet.json")
if not os.path.exists(path):
    print(f"File not found: {path}")
else:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Last updated: {data.get('updated_at')}")
    falta_abrir = data.get("falta_abrir", [])
    if len(falta_abrir) > 0:
        first_item = falta_abrir[0]
        print(f"Keys in first item: {list(first_item.keys())}")
        print(f"UF: {first_item.get('UF')}")
        print(f"Município: {first_item.get('Município')}")
        print(f"Parceiro: {first_item.get('Parceiro')}")
        print(f"Nome: {first_item.get('Nome da Escola')}")
    else:
        print("falta_abrir is empty")
