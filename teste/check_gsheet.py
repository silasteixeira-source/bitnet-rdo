import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from unificador_auto import get_gspread_client

url = 'https://docs.google.com/spreadsheets/d/1Onw1vaSO2SIQ_OfAoDPI6ycnXWTAZ2ijhtujAOhI9UM/edit?usp=sharing'

print("Tentando conectar no Google Sheets via gspread...")
try:
    client = get_gspread_client()
    if client:
        sheet = client.open_by_url(url).sheet1
        rows = sheet.get_all_records()
        if rows:
            print("Colunas encontradas:", list(rows[0].keys()))
            print("Exemplo linha 1:", rows[0])
            
            # Testa para o INEP 21289930
            inep = '21289930'
            for row in rows:
                if inep in str(row.values()):
                    print(f"ACHOU O INEP {inep}:", row)
                    break
        else:
            print("Planilha vazia.")
    else:
        print("Erro: Nao conectou no gspread.")
except Exception as e:
    print(f"Erro: {e}")
