import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="Pesquisa Local INEP", layout="wide")

st.title("🔎 Pesquisa Visual por INEP")
st.markdown("Esta é uma ferramenta **100% local** focada em trazer todas as informações de um INEP específico usando o novo banco de dados SQLite.")

inep_busca = st.text_input("Digite o INEP (ou parte dele) e pressione Enter:")

if inep_busca:
    db_path = "acompanhamento.db"
    if not os.path.exists(db_path):
        st.error(f"Banco de dados não encontrado em {db_path}")
    else:
        conn = sqlite3.connect(db_path)
        # Vamos pesquisar na coluna INEP_CORRETO, ignorando espaços
        query = f"SELECT * FROM operacional WHERE INEP_CORRETO LIKE '%{inep_busca}%'"
        
        try:
            df = pd.read_sql_query(query, conn)
            if not df.empty:
                st.success(f"Encontrado(s) {len(df)} registro(s) para o INEP {inep_busca}")
                
                # Se for apenas 1 resultado, mostrar de forma vertical (mais fácil de ler as 50+ colunas)
                if len(df) == 1:
                    st.write("### Ficha Completa do INEP")
                    # Removemos colunas que estão vazias para limpar a visão
                    df_limpo = df.dropna(axis=1, how='all')
                    
                    # Transpor para visualização vertical (Chave - Valor)
                    df_transposto = df_limpo.T.reset_index()
                    df_transposto.columns = ["Campo", "Valor"]
                    
                    st.dataframe(df_transposto, use_container_width=True, hide_index=True)
                else:
                    st.write("### Registros Encontrados")
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"Nenhum registro encontrado para o INEP: {inep_busca}")
        except Exception as e:
            st.error(f"Erro ao pesquisar: {e}")
        finally:
            conn.close()
