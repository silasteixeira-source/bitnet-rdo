import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Verificador de Chamados", page_icon="🎫", layout="wide")

st.title("🎫 Verificador de Chamados Abertos (OS)")
st.markdown("Faça o upload da planilha **Controle de OS** e do relatório de **Controladoras Offline** (gerado pelo Comparador) para descobrir quais locais já possuem chamado e em quais ainda é necessário atuar.")

col1, col2 = st.columns(2)
with col1:
    st.info("📊 Arquivo de Controle de OS")
    os_file = st.file_uploader("Upload da Planilha Controle_OS", type=["xlsx", "xls"], key="os")

with col2:
    st.error("🔴 Relatório de Offline (Comparativo)")
    offline_file = st.file_uploader("Upload da Planilha do Comparador (Omada)", type=["xlsx", "xls"], key="offline")

if st.button("🔍 Cruzar Dados", type="primary", use_container_width=True):
    if not os_file or not offline_file:
        st.warning("⚠️ Por favor, faça o upload das duas planilhas antes de analisar.")
    else:
        try:
            with st.spinner("Analisando chamados..."):
                # 1. Carregar OS
                df_os = pd.read_excel(os_file)
                
                # Garantir colunas necessárias
                if 'INEP' not in df_os.columns or 'Status' not in df_os.columns:
                    st.error("A planilha de Controle de OS precisa conter as colunas 'INEP' e 'Status'.")
                    st.stop()
                    
                # 2. Filtrar chamados em aberto (eliminando concluídos e cancelados)
                df_os_abertos = df_os[~df_os['Status'].astype(str).str.upper().str.contains('CONCLUÍDO|CONCLUIDO|CANCELADO|FECHADO', regex=True, na=False)].copy()
                
                # 3. Pegar lista de INEPs que possuem chamado aberto
                ineps_com_chamado = df_os_abertos['INEP'].dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()
                
                # 4. Carregar Relatório de Offline
                # A planilha do Comparativo tem as abas 'Novas_Offline' e 'Ainda_Offline'
                # Vamos ler todas as abas que contém "offline" e consolidar
                xl = pd.ExcelFile(offline_file)
                df_offline_list = []
                for sheet in xl.sheet_names:
                    if 'offline' in sheet.lower():
                        df_sheet = xl.parse(sheet)
                        df_offline_list.append(df_sheet)
                
                if not df_offline_list:
                    # Se por acaso não achar pelo nome, tenta ler a primeira aba
                    df_offline = xl.parse(0)
                else:
                    df_offline = pd.concat(df_offline_list, ignore_index=True)
                
                # 5. Extrair INEP da planilha offline
                # Procuramos a primeira coluna que deve ser a de Nome para extrair o INEP
                col_name = 'NAME' if 'NAME' in df_offline.columns else df_offline.columns[0]
                df_offline['INEP_Extraido'] = df_offline[col_name].astype(str).str.extract(r'(\d{6,})')[0]
                
                # 6. Cruzar e Separar os dois grupos
                mask_tem_chamado = df_offline['INEP_Extraido'].isin(ineps_com_chamado)
                
                df_falta_abrir = df_offline[~mask_tem_chamado].copy()
                df_ja_aberto = df_offline[mask_tem_chamado].copy()
                
                # Enriquecer quem JÁ TEM chamado com as informações do ticket (Ticket#, Atribuído a, etc)
                df_os_abertos_unico = df_os_abertos.drop_duplicates(subset=['INEP'], keep='first')
                df_os_abertos_unico['INEP'] = df_os_abertos_unico['INEP'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                # Merge apenas das colunas úteis
                colunas_merge = ['INEP', 'Ticket#', 'Status', 'Atribuído a']
                # Pega as que existem
                colunas_merge = [c for c in colunas_merge if c in df_os_abertos_unico.columns]
                
                df_ja_aberto = df_ja_aberto.merge(df_os_abertos_unico[colunas_merge], 
                                                  left_on='INEP_Extraido', right_on='INEP', how='left')
                if 'INEP' in df_ja_aberto.columns:
                    df_ja_aberto = df_ja_aberto.drop(columns=['INEP'])
                
                st.divider()
                st.subheader("📊 Resultados do Cruzamento")
                
                tab1, tab2 = st.tabs([
                    f"🚨 Falta Abrir Chamado ({len(df_falta_abrir)})", 
                    f"🎫 Já Possui Chamado ({len(df_ja_aberto)})"
                ])
                
                with tab1:
                    st.markdown("### Controladoras Offline SEM chamado aberto")
                    st.write("Estas controladoras constam como Offline, mas **NÃO possuem registro de chamado** em andamento na planilha de OS.")
                    st.dataframe(df_falta_abrir, use_container_width=True)
                
                with tab2:
                    st.markdown("### Controladoras Offline COM chamado em andamento")
                    st.write("Já existe um chamado sendo tratado para estes locais. (Os dados do Ticket foram adicionados no final da tabela).")
                    st.dataframe(df_ja_aberto, use_container_width=True)
                
                st.divider()
                st.subheader("📥 Exportar Relatório de Ação")
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if not df_falta_abrir.empty: df_falta_abrir.to_excel(writer, index=False, sheet_name='Falta_Abrir_Chamado')
                    if not df_ja_aberto.empty: df_ja_aberto.to_excel(writer, index=False, sheet_name='Chamados_Abertos')
                
                st.download_button(
                    label="📥 Baixar Relatório (Excel)",
                    data=output.getvalue(),
                    file_name="Relatorio_Acao_Chamados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
                
        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado: {str(e)}")
