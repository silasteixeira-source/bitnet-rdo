import streamlit as st
import pandas as pd
import io
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def authenticate_gspread():
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    return None

def update_gsheet_tab(client, spreadsheet_url, sheet_name, df):
    sheet = client.open_by_url(spreadsheet_url)
    try:
        worksheet = sheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
    
    worksheet.clear()
    if not df.empty:
        df_str = df.fillna("").astype(str)
        worksheet.update([df_str.columns.values.tolist()] + df_str.values.tolist())
    else:
        worksheet.update([["Nenhum dado encontrado"]])

st.set_page_config(page_title="Verificador de Chamados", page_icon="🎫", layout="wide")

st.title("🎫 Verificador de Chamados Abertos (OS)")
st.markdown("Faça o upload do **Controle de OS**, do relatório gerado pelo **Comparador** e do **RDO** para descobrir quais locais válidos já possuem chamado e onde é necessário atuar.")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📊 Arquivo Controle de OS")
    os_file = st.file_uploader("Upload da Planilha OS", type=["xlsx", "xls"], key="os")

with col2:
    st.error("🔴 Relatório do Comparador")
    offline_file = st.file_uploader("Upload do Comparativo_Evolução", type=["xlsx", "xls"], key="offline")

with col3:
    st.success("📁 Arquivo RDO Oficial")
    rdo_file = st.file_uploader("Upload da Planilha RDO", type=["xlsx", "xls"], key="rdo")

st.divider()

with st.expander("⚙️ Configuração RDO (Como ler o INEP?)", expanded=False):
    modo_coluna_inep = st.radio(
        "Identificar coluna no RDO:", 
        ["Pela posição (Coluna M)", "Pelo nome da coluna"]
    )
    nome_col_inep = ""
    if modo_coluna_inep == "Pelo nome da coluna":
        nome_col_inep = st.text_input("Digite o nome da coluna:", value="INEP")

if st.button("🔍 Cruzar Dados", type="primary", use_container_width=True):
    if not os_file or not offline_file or not rdo_file:
        st.warning("⚠️ Por favor, faça o upload das TRÊS planilhas antes de analisar.")
    else:
        try:
            with st.spinner("Analisando chamados cruzados com o RDO..."):
                # 1. Carregar RDO
                df_rdo = pd.read_excel(rdo_file)
                if modo_coluna_inep == "Pela posição (Coluna M)":
                    if df_rdo.shape[1] > 12:
                        serie_inep = df_rdo.iloc[:, 12]
                    else:
                        st.error("A planilha RDO não possui a coluna M.")
                        st.stop()
                else:
                    if nome_col_inep not in df_rdo.columns:
                        st.error(f"A coluna '{nome_col_inep}' não foi encontrada no RDO.")
                        st.stop()
                    serie_inep = df_rdo[nome_col_inep]
                
                ineps_rdo = serie_inep.dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()

                # 2. Carregar OS
                df_os = pd.read_excel(os_file)
                if 'INEP' not in df_os.columns or 'Status' not in df_os.columns:
                    st.error("A planilha de Controle de OS precisa conter as colunas 'INEP' e 'Status'.")
                    st.stop()
                    
                df_os_abertos = df_os[~df_os['Status'].astype(str).str.upper().str.contains('CONCLUÍDO|CONCLUIDO|CANCELADO|FECHADO', regex=True, na=False)].copy()
                ineps_com_chamado = df_os_abertos['INEP'].dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()
                
                # 3. Carregar Relatório de Offline (Comparador)
                xl = pd.ExcelFile(offline_file)
                df_offline_list = []
                df_recuperadas_list = []
                
                for sheet in xl.sheet_names:
                    if 'offline' in sheet.lower():
                        df_sheet = xl.parse(sheet)
                        df_offline_list.append(df_sheet)
                    elif 'recuperadas' in sheet.lower():
                        df_sheet = xl.parse(sheet)
                        df_recuperadas_list.append(df_sheet)
                
                if not df_offline_list:
                    df_offline = xl.parse(0)
                else:
                    df_offline = pd.concat(df_offline_list, ignore_index=True)
                    
                df_recuperadas = pd.concat(df_recuperadas_list, ignore_index=True) if df_recuperadas_list else pd.DataFrame()
                
                # 4. Extrair INEP da planilha offline e das recuperadas
                col_name_off = 'NAME' if 'NAME' in df_offline.columns else df_offline.columns[0]
                df_offline['INEP_Extraido'] = df_offline[col_name_off].astype(str).str.extract(r'(\d{6,})')[0]
                
                if not df_recuperadas.empty:
                    col_name_rec = 'NAME' if 'NAME' in df_recuperadas.columns else df_recuperadas.columns[0]
                    df_recuperadas['INEP_Extraido'] = df_recuperadas[col_name_rec].astype(str).str.extract(r'(\d{6,})')[0]
                
                # 5. Cruzar grupos - REGRA DE NEGÓCIO: SÓ ABRIR SE ESTIVER NO RDO
                mask_no_rdo = df_offline['INEP_Extraido'].isin(ineps_rdo)
                df_validos = df_offline[mask_no_rdo].copy()
                df_ignorados = df_offline[~mask_no_rdo].copy()
                
                # Dos válidos (que estão no RDO), verificamos se já tem chamado
                mask_tem_chamado = df_validos['INEP_Extraido'].isin(ineps_com_chamado)
                df_falta_abrir = df_validos[~mask_tem_chamado].copy()
                df_ja_aberto = df_validos[mask_tem_chamado].copy()
                
                # Cruzar grupo de Recuperadas
                df_fechar_chamado = pd.DataFrame()
                if not df_recuperadas.empty:
                    mask_rec_com_chamado = df_recuperadas['INEP_Extraido'].isin(ineps_com_chamado)
                    df_fechar_chamado = df_recuperadas[mask_rec_com_chamado].copy()
                
                # 6. Enriquecer planilhas com dados da OS
                df_os_abertos_unico = df_os_abertos.drop_duplicates(subset=['INEP'], keep='first')
                df_os_abertos_unico['INEP'] = df_os_abertos_unico['INEP'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                
                colunas_merge = ['INEP', 'Ticket#', 'Status', 'Atribuído a']
                colunas_merge = [c for c in colunas_merge if c in df_os_abertos_unico.columns]
                
                # Merge Já Aberto
                df_ja_aberto = df_ja_aberto.merge(df_os_abertos_unico[colunas_merge], left_on='INEP_Extraido', right_on='INEP', how='left')
                if 'INEP' in df_ja_aberto.columns: df_ja_aberto = df_ja_aberto.drop(columns=['INEP'])
                    
                # Merge Recuperadas
                if not df_fechar_chamado.empty:
                    df_fechar_chamado = df_fechar_chamado.merge(df_os_abertos_unico[colunas_merge], left_on='INEP_Extraido', right_on='INEP', how='left')
                    if 'INEP' in df_fechar_chamado.columns: df_fechar_chamado = df_fechar_chamado.drop(columns=['INEP'])
                
                st.divider()
                st.subheader("📊 Resultados do Cruzamento (Validados pelo RDO)")
                
                tab1, tab2, tab3, tab4 = st.tabs([
                    f"🚨 Falta Abrir Chamado ({len(df_falta_abrir)})", 
                    f"🎫 Já Possui Chamado ({len(df_ja_aberto)})",
                    f"🟢 Fechar Chamado ({len(df_fechar_chamado)})",
                    f"🚫 Ignorados - Fora do RDO ({len(df_ignorados)})"
                ])
                
                with tab1:
                    st.markdown("### Controladoras Válidas SEM chamado aberto")
                    st.write("Estão Offline, **constam no RDO**, mas **NÃO possuem registro de chamado**.")
                    st.dataframe(df_falta_abrir, use_container_width=True)
                
                with tab2:
                    st.markdown("### Controladoras Válidas COM chamado em andamento")
                    st.write("Já existe um chamado ativo sendo tratado para estes locais.")
                    st.dataframe(df_ja_aberto, use_container_width=True)
                    
                with tab3:
                    st.markdown("### Controladoras que Voltaram a Funcionar (COM chamado aberto)")
                    st.write("Estavam offline, **voltaram a ficar online**, mas ainda possuem chamado aberto na OS!")
                    st.dataframe(df_fechar_chamado if not df_fechar_chamado.empty else pd.DataFrame(columns=['Nenhum chamado para fechar']), use_container_width=True)

                with tab4:
                    st.markdown("### Controladoras Offline FORA do RDO (Ignoradas)")
                    st.write("Estas controladoras estão offline no Omada, mas **NÃO constam na planilha RDO**. Portanto, nenhum chamado deve ser aberto para elas.")
                    st.dataframe(df_ignorados if not df_ignorados.empty else pd.DataFrame(columns=['Tudo certo!']), use_container_width=True)
                
                st.divider()
                st.subheader("📥 Exportar Relatório Final")
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    if not df_falta_abrir.empty: df_falta_abrir.to_excel(writer, index=False, sheet_name='Falta_Abrir_Chamado')
                    if not df_ja_aberto.empty: df_ja_aberto.to_excel(writer, index=False, sheet_name='Chamados_Abertos')
                    if not df_fechar_chamado.empty: df_fechar_chamado.to_excel(writer, index=False, sheet_name='Fechar_Chamado_Recuperadas')
                    if not df_ignorados.empty: df_ignorados.to_excel(writer, index=False, sheet_name='Ignorados_Fora_do_RDO')
                
                st.download_button(
                    label="📥 Baixar Relatório Completo (Excel)",
                    data=output.getvalue(),
                    file_name="Relatorio_Acao_Chamados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
                
                st.divider()
                st.subheader("☁️ Sincronizar com Google Sheets")
                gsheet_url = st.text_input("URL da Planilha", value="https://docs.google.com/spreadsheets/d/167LUrFFBJBlQ-Jh7cX717r32F2c8tfq1zsx_0FIC0WY/edit")
                
                if st.button("🚀 Sincronizar Agora (Sobrescrever)", type="secondary", use_container_width=True):
                    client = authenticate_gspread()
                    if client:
                        with st.spinner("Limpando dados antigos e enviando novos para a nuvem..."):
                            try:
                                update_gsheet_tab(client, gsheet_url, "Falta_Abrir_Chamado", df_falta_abrir)
                                update_gsheet_tab(client, gsheet_url, "Chamados_Abertos", df_ja_aberto)
                                update_gsheet_tab(client, gsheet_url, "Fechar_Chamado_Recup", df_fechar_chamado)
                                update_gsheet_tab(client, gsheet_url, "Ignorados_Fora_do_RDO", df_ignorados)
                                st.success("✅ Planilha Google atualizada com sucesso! Verifique as abas online.")
                            except Exception as e_sheet:
                                st.error(f"❌ Erro ao atualizar o Google Sheets: {e_sheet}")
                    else:
                        st.error("❌ Credenciais do Google não encontradas no arquivo secrets.")
                
        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado: {str(e)}")
