import pandas as pd
from datetime import datetime

escolas_eace_map = {
    '123456': {
        'nome': 'Escola Teste',
        'uf': 'SP',
        'municipio': 'São Paulo',
        'parceiro': 'XPTO'
    }
}

df_alvo = pd.DataFrame({
    'INEP_Extraido': ['123456', '999999'],
    'description': ['a', 'b']
})

cols_remover_omada_set = {'description'}
hora_execucao_br = "agora"

def formatar_e_limpar(df_alvo):
    if not isinstance(df_alvo, pd.DataFrame):
        return df_alvo
    cols_drop = [c for c in df_alvo.columns if str(c).strip().lower() in cols_remover_omada_set]
    df_alvo = df_alvo.drop(columns=cols_drop, errors='ignore')
    
    if 'INEP_Extraido' in df_alvo.columns:
        inep_series = df_alvo['INEP_Extraido'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df_alvo['Nome da Escola'] = inep_series.apply(lambda x: escolas_eace_map.get(x, {}).get('nome', "Não Cadastrado na EACE"))
        df_alvo['UF'] = inep_series.apply(lambda x: escolas_eace_map.get(x, {}).get('uf', "-"))
        df_alvo['Município'] = inep_series.apply(lambda x: escolas_eace_map.get(x, {}).get('municipio', "-"))
        df_alvo['Parceiro'] = inep_series.apply(lambda x: escolas_eace_map.get(x, {}).get('parceiro', "-"))
        
        cols = list(df_alvo.columns)
        if 'Nome da Escola' in cols:
            cols.remove('Nome da Escola')
            pos = cols.index('INEP_Extraido') + 1 if 'INEP_Extraido' in cols else 1
            cols.insert(pos, 'Nome da Escola')
            df_alvo = df_alvo[cols]
            
    df_alvo['Atualizado Em'] = hora_execucao_br
    return df_alvo.fillna("")

res = formatar_e_limpar(df_alvo)
print(res.to_dict(orient='records'))
