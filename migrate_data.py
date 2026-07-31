import pandas as pd
import sqlite3
import os

# Caminhos
excel_path = r'c:\Users\ADM\Documents\NOC\Arquivos\Automação\AcompanhamentoOPE\Acompanhamento Operacional.xlsx'
db_path = r'c:\Users\ADM\Documents\NOC\Arquivos\Automação\RDO\acompanhamento.db'

print(f"Lendo o arquivo Excel: {excel_path}")
xls = pd.ExcelFile(excel_path)

# Abas que representam estados
abas_estados = ['MA', 'CE', 'PA', 'RN', 'PI', 'BA']

# Lista para guardar os dataframes
dfs = []

for aba in abas_estados:
    if aba in xls.sheet_names:
        print(f"Lendo aba: {aba}")
        df = pd.read_excel(xls, sheet_name=aba)
        # Adicionar a coluna de UF para identificar de onde veio
        df['UF'] = aba
        dfs.append(df)

if dfs:
    # Juntar todos os dataframes em um só
    df_consolidado = pd.concat(dfs, ignore_index=True)
    
    # Limpar nomes de colunas
    df_consolidado.columns = df_consolidado.columns.str.strip().str.upper()
    
    # Renomear colunas duplicadas
    cols = pd.Series(df_consolidado.columns)
    for dup in cols[cols.duplicated()].unique():
        indices = cols[cols == dup].index.values.tolist()
        cols[indices] = [f"{dup}_{i}" if i != 0 else dup for i in range(len(indices))]
    df_consolidado.columns = cols
    
    # Resolver problemas de Timestamp com SQLite
    for col in df_consolidado.select_dtypes(include=['datetime', 'datetimetz']).columns:
        df_consolidado[col] = df_consolidado[col].astype(str)
    for col in df_consolidado.select_dtypes(include=['object']).columns:
        df_consolidado[col] = df_consolidado[col].apply(lambda x: str(x) if pd.notnull(x) else '')
    
    # Adicionar um ID único
    df_consolidado.insert(0, 'ID', range(1, 1 + len(df_consolidado)))
    
    print(f"Total de linhas lidas: {len(df_consolidado)}")
    
    # Conectar ao banco de dados SQLite
    conn = sqlite3.connect(db_path)
    
    # Exportar o DataFrame para o banco
    print("Exportando para o banco de dados SQLite...")
    df_consolidado.to_sql('operacional', conn, if_exists='replace', index=False)
    
    conn.close()
    print(f"Migração concluída com sucesso! Banco salvo em: {db_path}")
else:
    print("Nenhuma aba de estado encontrada para migrar.")
