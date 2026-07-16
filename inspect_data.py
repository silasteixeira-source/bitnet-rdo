import pandas as pd

path1 = r"c:\Users\ADM\Documents\NOC\Arquivos\Automação\RDO\omada.xlsx"
df1 = pd.read_excel(path1, sheet_name=0)

print("Amostra OMADA (CSV):")
print(df1.head(5).to_csv(index=False))

path2 = r"c:\Users\ADM\Documents\NOC\Arquivos\Automação\RDO\rdoatualizado1.xlsx"
df2 = pd.read_excel(path2, sheet_name=0)

print("\nAmostra RDOATUALIZADO1 (CSV):")
print(df2.head(5).to_csv(index=False))
