import sys
import os
import streamlit as st
import pandas as pd

# Adicionar diretório raiz para importar utils_omada
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

import utils_omada

st.set_page_config(page_title="Monitor Omada Exporter", page_icon="⚡", layout="wide")

st.title("⚡ Monitor e Base Automática — Omada Exporter")
st.markdown(
    """
    Esta aba acompanha em tempo real a coleta automática de dados do **TP-Link Omada Cloud** realizada pelo serviço em segundo plano (`omada_exporter`).
    Aqui você pode auditar a saúde da base local, buscar controladoras e fazer download da versão mais recente a qualquer momento.
    """
)

# Botão para atualizar status da tela
col_btn, _ = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Atualizar Status Agora", use_container_width=True):
        st.rerun()

st.divider()

# Ler metadados do arquivo local
info = utils_omada.get_omada_file_info()

# Cards de Métricas
c1, c2, c3, c4 = st.columns(4)

if info["exists"]:
    with c1:
        st.metric(label="Status da Base", value="Ativa 🟢", delta="Disponível em disco")
    with c2:
        st.metric(label="Última Atualização", value=info["mtime_str"])
    with c3:
        if info["age_minutes"] == 0:
            age_txt = "< 1 min"
        elif info["age_minutes"] < 60:
            age_txt = f"{info['age_minutes']} min"
        else:
            h = info["age_minutes"] // 60
            m = info["age_minutes"] % 60
            age_txt = f"{h}h {m}min"
        st.metric(label="Tempo Desde a Coleta", value=age_txt)
    with c4:
        st.metric(label="Tamanho do Arquivo", value=f"{info['size_kb']} KB")
else:
    with c1:
        st.metric(label="Status da Base", value="Não Encontrada 🔴")
    with c2:
        st.metric(label="Última Atualização", value="--")
    with c3:
        st.metric(label="Tempo Desde a Coleta", value="--")
    with c4:
        st.metric(label="Tamanho do Arquivo", value="0 KB")

st.divider()

# Inspecionar e Filtrar Dados da Base
if info["exists"]:
    st.subheader("📋 Auditoria e Pré-visualização dos Dados")
    
    df = utils_omada.load_omada_auto_df()
    
    if df is not None and not df.empty:
        st.write(f"Total de registros na base: **{len(df)} controladoras / dispositivos**")
        
        # Filtro rápido
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            query = st.text_input("🔍 Buscar por nome, MAC ou IP:", placeholder="Digite para filtrar a tabela...")
        
        # Filtro de Status caso exista coluna com palavra STATUS ou STATE
        col_status_names = [c for c in df.columns if "STATUS" in str(c).upper() or "ESTADO" in str(c).upper()]
        status_selecionado = "Todos"
        if col_status_names:
            col_stat = col_status_names[0]
            valores_unicos = ["Todos"] + sorted(df[col_stat].dropna().astype(str).unique().tolist())
            with col_f2:
                status_selecionado = st.selectbox(f"Filtrar por {col_stat}:", valores_unicos)
        
        # Aplicar filtros no dataframe
        df_exibicao = df.copy()
        if query:
            mask = df_exibicao.astype(str).apply(lambda s: s.str.contains(query, case=False, na=False)).any(axis=1)
            df_exibicao = df_exibicao[mask]
        
        if col_status_names and status_selecionado != "Todos":
            df_exibicao = df_exibicao[df_exibicao[col_status_names[0]].astype(str) == status_selecionado]
            
        st.dataframe(df_exibicao, use_container_width=True, height=400)
        
        # Botão para download direto pelo Streamlit
        with open(info["path"], "rb") as fp:
            st.download_button(
                label="📥 Baixar Cópia da Planilha (omada_dados.xlsx)",
                data=fp,
                file_name="omada_dados_atualizado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
    else:
        st.warning("⚠️ O arquivo existe em disco, mas parece estar vazio ou em um formato não reconhecido pelo Pandas.")
else:
    st.warning(
        """
        ⚠️ **Nenhuma base de dados exportada foi encontrada na pasta `omada_exporter/dados_omada/`.**
        
        Para ativar a coleta automática:
        1. Abra a pasta `omada_exporter/` no seu computador.
        2. Dê um duplo clique no arquivo **`iniciar.bat`** (Windows) ou execute `./iniciar.sh` (Linux).
        3. O robô irá iniciar e salvará a planilha automaticamente a cada ciclo.
        """
    )
    
    st.info("💡 Assim que o exportador concluir o primeiro download, clique no botão **'🔄 Atualizar Status Agora'** no topo desta página.")
