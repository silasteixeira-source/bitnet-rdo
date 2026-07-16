import pandas as pd
import json

path1 = r"c:\Users\ADM\Documents\NOC\Arquivos\Automação\RDO\controle_OS.xlsx"

try:
    df1 = pd.read_excel(path1, sheet_name=0)
    print("Columns:", list(df1.columns))
    print("Head:\n", df1.head(3).to_csv(index=False))
except Exception as e:
    print("Error reading controle_OS.xlsx:", e)
