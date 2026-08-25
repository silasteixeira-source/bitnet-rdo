import pandas as pd

try:
    df = pd.read_excel('controle_OS (1).xlsx', engine='openpyxl')
    print("Colunas encontradas:")
    for i, col in enumerate(df.columns):
        print(f"[{i}] {col}")
    
    ineps_unicos = df['INEP'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).unique()
    print(f"Total de linhas: {len(df)}")
    print(f"Total de INEPs únicos: {len(ineps_unicos)}")
            
except Exception as e:
    print(f"Erro: {e}")
