import os
import sys
import pandas as pd

sys.path.append(os.getcwd())
try:
    from unificador_auto import get_gspread_client
except Exception as e:
    print(f"Erro ao importar unificador_auto: {e}")
    sys.exit(1)

def main():
    client = get_gspread_client()
    if not client:
        print("Erro: Não foi possível autenticar no GSpread.")
        return
        
    try:
        sh = client.open_by_key('1Onw1vaSO2SIQ_OfAoDPI6ycnXWTAZ2ijhtujAOhI9UM')
        ws = sh.worksheet('EACE')
        data = ws.get_all_values()
        if len(data) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            print("=== COLUNAS ENCONTRADAS NA PLANILHA EACE ===")
            for i, col in enumerate(df.columns):
                print(f"[{i}] {col}")
                
            print("\n=== AMOSTRA DA PRIMEIRA LINHA ===")
            print(df.iloc[0].to_dict())
        else:
            print("Planilha vazia ou sem cabeçalhos.")
    except Exception as e:
        print(f"Erro ao acessar planilha: {e}")

if __name__ == "__main__":
    main()
