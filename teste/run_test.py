import sys
import os

# Adiciona a pasta pai ao PYTHONPATH para importar o unificador_auto
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from unificador_auto import processar_fluxo

# Arquivos de teste
omada_file = "OrganizationList_2026-09-03-13-26.xlsx"
os_file = "controle_OS.xlsx"
rdo_file = "RDOST1.xlsx"

print("Iniciando teste local...")
processar_fluxo(
    omada_old_path=omada_file,
    omada_new_path=omada_file,
    os_path=os_file,
    rdo_path=rdo_file,
    sync_google=False,  # NÃO altera o Google Sheets de verdade!
    tenant="teste_resultado"
)
print("Teste concluído! Verificando snapshot gerado...")

import json
snapshot_path = os.path.join(parent_dir, ".streamlit", "snapshots", "teste_resultado.json")

if os.path.exists(snapshot_path):
    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print("\n=== RESULTADO DO TESTE ===")
    print(f"Falta Abrir: {len(data.get('falta_abrir', []))} escolas")
    print(f"Já Aberto: {len(data.get('abertos', []))} escolas")
    print(f"Fechar Chamado: {len(data.get('fechar', []))} escolas")
    print("--------------------------")
    
    # Vamos checar quantas estão CRÍTICAS (>4h) no Falta Abrir
    criticos = 0
    for e in data.get('falta_abrir', []):
        if ">4h" in str(e.get('Regra', '')):
            criticos += 1
            
    print(f"Dentre as de 'Falta Abrir', há {criticos} com Regra de CRÍTICO (>4h).")
    
else:
    print("Erro: JSON Snapshot não foi gerado.")
