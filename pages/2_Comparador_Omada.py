import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Comparador OMADA", page_icon="🔄", layout="wide")

st.title("🔄 Comparador de Status OMADA")
st.markdown("Faça o upload de duas planilhas do Omada (uma antiga/base e uma nova) para comparar a evolução do status das controladoras.")

col1, col2 = st.columns(2)
with col1:
    st.info("🕒 Arquivo Antigo (Base)")
    old_file = st.file_uploader("Upload da Planilha Omada Antiga", type=["xlsx", "xls"], key="old")

with col2:
    st.success("🆕 Arquivo Novo (Atual)")
    new_file = st.file_uploader("Upload da Planilha Omada Nova", type=["xlsx", "xls"], key="new")

def get_offline_controllers(df):
    """Retorna um DataFrame apenas com as controladoras offline e identifica as colunas chave."""
    col_name = 'NAME' if 'NAME' in df.columns else df.columns[0]
    col_status = None
    for col in df.columns:
        if 'status' in str(col).lower():
            col_status = col
            break
            
    if col_status is None:
        raise ValueError("A coluna 'STATUS' não foi encontrada na planilha.")
        
    cond_status = df[col_status].astype(str).str.upper().str.contains('OFFLINE')
    df_offline = df[cond_status].copy()
    
    # Remover eventuais duplicatas pelo nome, para não bagunçar a comparação
    df_offline = df_offline.drop_duplicates(subset=[col_name])
    return df_offline, col_name, col_status

if st.button("🚀 Comparar Status", type="primary", use_container_width=True):
    if not old_file or not new_file:
        st.warning("⚠️ Por favor, faça o upload das duas planilhas antes de comparar.")
    else:
        try:
            with st.spinner("Analisando e cruzando os dados..."):
                df_old = pd.read_excel(old_file)
                df_new = pd.read_excel(new_file)
                
                df_offline_old, name_col_old, status_col_old = get_offline_controllers(df_old)
                df_offline_new, name_col_new, status_col_new = get_offline_controllers(df_new)
                
                # Pegar apenas os nomes das controladoras offline
                set_old = set(df_offline_old[name_col_old].astype(str).str.strip())
                set_new = set(df_offline_new[name_col_new].astype(str).str.strip())
                
                # Lógica de Conjuntos
                novas_offline_names = set_new - set_old
                ainda_offline_names = set_new.intersection(set_old)
                recuperadas_names = set_old - set_new # Extra: as que voltaram a ficar online!
                
                # Extraindo as linhas originais correspondentes da planilha NOVA para as 'Novas' e 'Ainda Offline'
                df_new['NOME_CLEAN'] = df_new[name_col_new].astype(str).str.strip()
                df_old['NOME_CLEAN'] = df_old[name_col_old].astype(str).str.strip()
                
                df_novas = df_new[df_new['NOME_CLEAN'].isin(novas_offline_names)].drop(columns=['NOME_CLEAN'])
                df_ainda = df_new[df_new['NOME_CLEAN'].isin(ainda_offline_names)].drop(columns=['NOME_CLEAN'])
                df_recuperadas = df_old[df_old['NOME_CLEAN'].isin(recuperadas_names)].drop(columns=['NOME_CLEAN'])
                
                st.divider()
                st.subheader("📊 Resultados da Comparação")
                
                # Usando Tabs para organizar melhor o resultado
                tab1, tab2, tab3 = st.tabs([
                    f"🔴 Novas Offline ({len(df_novas)})", 
                    f"⚠️ Ainda Offline ({len(df_ainda)})",
                    f"🟢 Recuperadas ({len(df_recuperadas)})"
                ])
                
                # Definir colunas para mostrar bonitinho na tela
                colunas_exibir_novas = [name_col_new, status_col_new]
                if 'MODEL' in df_new.columns: colunas_exibir_novas.append('MODEL')
                    
                with tab1:
                    st.markdown("### Controladoras que caíram")
                    st.write("Estavam online na planilha antiga, mas ficaram **OFFLINE** na planilha nova.")
                    st.dataframe(df_novas[colunas_exibir_novas] if not df_novas.empty else df_novas, use_container_width=True)
                
                with tab2:
                    st.markdown("### Controladoras sem solução")
                    st.write("Já estavam offline na planilha antiga e **CONTINUAM OFFLINE** na planilha nova.")
                    st.dataframe(df_ainda[colunas_exibir_novas] if not df_ainda.empty else df_ainda, use_container_width=True)
                    
                with tab3:
                    st.markdown("### Controladoras que voltaram (Bônus!)")
                    st.write("Estavam offline na planilha antiga, mas agora estão **ONLINE** na planilha nova.")
                    # Para as recuperadas, usamos as colunas do df_old
                    colunas_exibir_old = [name_col_old, status_col_old]
                    if 'MODEL' in df_old.columns: colunas_exibir_old.append('MODEL')
                    st.dataframe(df_recuperadas[colunas_exibir_old] if not df_recuperadas.empty else df_recuperadas, use_container_width=True)
                
                st.divider()
                st.subheader("📥 Exportar Relatório")
                
                # Gerar Excel em memória
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if not df_novas.empty: df_novas.to_excel(writer, index=False, sheet_name='Novas_Offline')
                    if not df_ainda.empty: df_ainda.to_excel(writer, index=False, sheet_name='Ainda_Offline')
                    if not df_recuperadas.empty: df_recuperadas.to_excel(writer, index=False, sheet_name='Recuperadas_Online')
                
                st.download_button(
                    label="📥 Baixar Relatório Completo (Excel)",
                    data=output.getvalue(),
                    file_name="Comparativo_Evolucao_Omada.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
                
        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado ao analisar: {str(e)}")
