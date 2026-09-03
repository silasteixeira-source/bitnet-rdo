import pandas as pd
import json

inep = '21289930'
df_omada = pd.read_excel('teste/OrganizationList_2026-09-03-13-26.xlsx')

print("--- EQUIPAMENTOS NO OMADA COM ESTE INEP ---")
matches = df_omada[df_omada['NAME'].astype(str).str.contains(inep)]
for _, row in matches.iterrows():
    print(f"Nome: {row.get('NAME')} -> Status: {row.get('STATUS')}")

print("\n--- POR QUE NAO ESTA NA LISTA FINAL? ---")
with open('.streamlit/snapshots/teste_resultado.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    
found_in_json = False
for k in data.keys():
    if isinstance(data[k], list):
        for item in data[k]:
            if inep in str(item):
                print(f"O INEP foi encontrado dentro da lista: {k}")
                found_in_json = True
                break

if not found_in_json:
    print("O INEP foi completamente removido da analise final (provavelmente pelo Filtro Anti-Falso-Offline).")
