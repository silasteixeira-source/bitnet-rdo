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

@st.cache_data(ttl=3600)
def get_escolas_eace_map():
    client = authenticate_gspread()
    if not client:
        return {}
    try:
        sh = client.open_by_key('1Onw1vaSO2SIQ_OfAoDPI6ycnXWTAZ2ijhtujAOhI9UM')
        ws = sh.worksheet('EACE')
        data = ws.get_all_values()
        if len(data) > 1:
            df_eace = pd.DataFrame(data[1:], columns=data[0])
            mapping = {
                str(r.iloc[3]).strip().replace('.0', ''): str(r.iloc[4]).strip()
                for _, r in df_eace.iterrows()
                if str(r.iloc[3]).strip()
            }
            return mapping
    except Exception as e:
        st.warning(f"Aviso: Não foi possível carregar mapeamento de escolas da EACE ({e})")
    return {}

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

st.set_page_config(page_title="Unificador Omada e Chamados", page_icon="⚡", layout="wide")

st.title("⚡ Fluxo Unificado: Omada & Chamados")
st.markdown("Faça o upload de todas as planilhas abaixo para cruzar automaticamente a evolução do Omada com o RDO e o Controle de OS.")

st.divider()

destino_planilha = st.radio(
    "Para qual cliente/projeto deseja rodar a unificação?",
    ["BITNET", "ST1"],
    horizontal=True
)

st.divider()

# Entradas
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("### 🕒 Omada Antigo")
    old_file = st.file_uploader("Upload Omada Base", type=["xlsx", "xls"], key="old")
with c2:
    st.markdown("### 🆕 Omada Novo")
    new_file = st.file_uploader("Upload Omada Atual", type=["xlsx", "xls"], key="new")
with c3:
    st.markdown("### 📊 Controle OS")
    os_file = st.file_uploader("Upload Planilha OS", type=["xlsx", "xls"], key="os")
with c4:
    st.markdown("### 📁 RDO")
    usar_rdo_google = st.checkbox("Usar RDO Oficial (Google Sheets)", value=True)
    if not usar_rdo_google:
        rdo_file = st.file_uploader("Upload Planilha RDO", type=["xlsx", "xls"], key="rdo")
    else:
        if destino_planilha == "BITNET":
            rdo_file = "https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit?gid=1631182129#gid=1631182129"
        else:
            rdo_file = "https://docs.google.com/spreadsheets/d/1IoTyZ4fmgUwvdLYtEC_9UqgIDBmuLH_o/edit?gid=483331132#gid=483331132"
        st.info(f"📌 Conectado ao RDO Oficial da {destino_planilha}.")

st.divider()

# Configurações Avançadas de Colunas (Ocultas por padrão)
with st.expander("⚙️ Configurações de Colunas (Apenas se a leitura falhar)"):
    st.write("Configuração RDO:")
    modo_coluna_inep = st.radio("Como achar o INEP no RDO?", ["Pela posição (Coluna M)", "Pelo nome da coluna"], horizontal=True)
    nome_col_inep = st.text_input("Nome da coluna (se escolheu nome):", value="INEP")
    
    st.write("Configuração Omada:")
    modo_config_omada = st.radio("Como achar NOME e STATUS no Omada?", ["Automático", "Manual"], horizontal=True)
    custom_name_col = st.text_input("Nome da coluna NAME:", value="NAME")
    custom_status_col = st.text_input("Nome da coluna STATUS:", value="STATUS")

# Lógica principal
def get_offline_controllers(df, force_name_col="", force_status_col=""):
    """Retorna controladoras offline e identifica colunas."""
    col_name = force_name_col if force_name_col else ('NAME' if 'NAME' in df.columns else df.columns[0])
    
    col_status = None
    if force_status_col:
        col_status = force_status_col
    else:
        for col in df.columns:
            if 'status' in str(col).lower():
                col_status = col
                break
                
    if col_status is None:
        raise ValueError("Coluna 'STATUS' não encontrada no Omada.")
        
    cond_status = df[col_status].astype(str).str.upper().str.contains('OFFLINE')
    df_offline = df[cond_status].copy()
    df_offline = df_offline.drop_duplicates(subset=[col_name])
    return df_offline, col_name, col_status

def sort_by_uptime(df, status_col):
    if df.empty or status_col not in df.columns:
        return df
    temp_dates = df[status_col].astype(str).str.extract(r'(?i)Uptime:\s*(.*)')[0]
    df['_temp_date'] = pd.to_datetime(temp_dates, errors='coerce')
    df = df.sort_values(by='_temp_date', ascending=False).drop(columns=['_temp_date'])
    return df

st.divider()
st.subheader("☁️ Configuração Google Sheets")
sync_google = st.checkbox("Sincronizar automaticamente após o processamento", value=True)

# URLs Padrões (Podem ser editadas pelo usuário se necessário)
default_bitnet = "https://docs.google.com/spreadsheets/d/167LUrFFBJBlQ-Jh7cX717r32F2c8tfq1zsx_0FIC0WY/edit"
default_st1 = "https://docs.google.com/spreadsheets/d/1jMc7SW8ECb49j1LP8W879Xz-wyxudkkMYCH9s7nKVdU/edit"
default_omada_bitnet = "https://docs.google.com/spreadsheets/d/1r8jQ8jJGWSLQoACVoBy8emYlk3avJOuEXM10W_tlY-o/edit?gid=998874036#gid=998874036"
default_omada_st1 = "https://docs.google.com/spreadsheets/d/1wDbFAKnbf62CvW7byBM5yXXMUAx2lwoquvOC59xJmN4/edit?gid=998874036#gid=998874036"

if destino_planilha == "BITNET":
    gsheet_url = st.text_input("URL da Planilha BITNET", value=default_bitnet)
    omada_gsheet_url = default_omada_bitnet
else:
    gsheet_url = st.text_input("URL da Planilha ST1", value=default_st1)
    omada_gsheet_url = default_omada_st1

st.write("")

if st.button("🚀 Processar Fluxo Completo", type="primary", use_container_width=True):
    if not (old_file and new_file and os_file and rdo_file):
        st.warning("⚠️ Faça o upload de TODAS as 4 planilhas antes de processar.")
    else:
        try:
            with st.spinner("1/3 - Cruzando Planilhas do Omada..."):
                # --- PASSO 1: COMPARADOR OMADA ---
                df_old = pd.read_excel(old_file)
                df_new = pd.read_excel(new_file)
                
                f_n = custom_name_col if modo_config_omada == "Manual" else ""
                f_s = custom_status_col if modo_config_omada == "Manual" else ""
                
                df_off_old, name_old, status_old = get_offline_controllers(df_old, f_n, f_s)
                df_off_new, name_new, status_new = get_offline_controllers(df_new, f_n, f_s)
                
                set_old = set(df_off_old[name_old].astype(str).str.strip())
                set_new = set(df_off_new[name_new].astype(str).str.strip())
                
                df_new['NOME_CLEAN'] = df_new[name_new].astype(str).str.strip()
                df_old['NOME_CLEAN'] = df_old[name_old].astype(str).str.strip()
                
                df_novas = df_new[df_new['NOME_CLEAN'].isin(set_new - set_old)].drop(columns=['NOME_CLEAN'])
                df_ainda = df_new[df_new['NOME_CLEAN'].isin(set_new.intersection(set_old))].drop(columns=['NOME_CLEAN'])
                df_recuperadas = df_old[df_old['NOME_CLEAN'].isin(set_old - set_new)].drop(columns=['NOME_CLEAN'])
                
                df_novas = sort_by_uptime(df_novas, status_new)
                df_ainda = sort_by_uptime(df_ainda, status_new)
                df_recuperadas = sort_by_uptime(df_recuperadas, status_old)
                
                # Consolidando Omada Offline para cruzamento
                df_offline = pd.concat([df_novas, df_ainda], ignore_index=True)
                
                # Extraindo INEP
                df_offline['INEP_Extraido'] = df_offline[name_new].astype(str).str.extract(r'(\d{6,})')[0]
                if not df_recuperadas.empty:
                    df_recuperadas['INEP_Extraido'] = df_recuperadas[name_old].astype(str).str.extract(r'(\d{6,})')[0]

            with st.spinner("2/3 - Validando INEPs com RDO..."):
                # --- PASSO 2: RDO ---
                if isinstance(rdo_file, str) and rdo_file.startswith("http"):
                    client_rdo = authenticate_gspread()
                    if not client_rdo:
                        st.error("❌ Falha ao conectar ao Google Sheets para ler o RDO.")
                        st.stop()
                    try:
                        sh_rdo = client_rdo.open_by_url(rdo_file)
                        try:
                            ws_rdo = sh_rdo.get_worksheet_by_id(1631182129)
                            if not ws_rdo:
                                ws_rdo = sh_rdo.sheet1
                        except Exception:
                            ws_rdo = sh_rdo.sheet1
                        data_rdo = ws_rdo.get_all_values()
                        df_rdo = pd.DataFrame(data_rdo[1:], columns=data_rdo[0]) if len(data_rdo) > 1 else pd.DataFrame()
                    except Exception as e_sheet:
                        try:
                            import re, io, requests, google.auth.transport.requests
                            match = re.search(r'/d/([a-zA-Z0-9_-]+)', rdo_file)
                            if not match:
                                raise ValueError("ID do arquivo Google Drive não encontrado na URL.")
                            req_auth = google.auth.transport.requests.Request()
                            client_rdo.http_client.auth.refresh(req_auth)
                            res = requests.get(f"https://www.googleapis.com/drive/v3/files/{match.group(1)}?alt=media", headers={"Authorization": f"Bearer {client_rdo.http_client.auth.token}"})
                            df_rdo = pd.read_excel(io.BytesIO(res.content)) if res.status_code == 200 else pd.DataFrame()
                        except Exception as e_drive:
                            st.error(f"❌ Falha ao carregar planilha RDO no Google Drive: {e_drive}")
                            st.stop()
                else:
                    df_rdo = pd.read_excel(rdo_file)

                if modo_coluna_inep == "Pela posição (Coluna M)":
                    serie_inep = df_rdo.iloc[:, 12]
                else:
                    serie_inep = df_rdo[nome_col_inep]
                
                ineps_rdo = serie_inep.dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()
                
                mask_no_rdo = df_offline['INEP_Extraido'].isin(ineps_rdo)
                df_validos = df_offline[mask_no_rdo].copy()
                df_ignorados = df_offline[~mask_no_rdo].copy()

            with st.spinner("3/3 - Cruzando com Controle de OS..."):
                # --- PASSO 3: CONTROLE DE OS ---
                df_os = pd.read_excel(os_file)
                df_os_abertos = df_os[~df_os['Status'].astype(str).str.upper().str.contains('CONCLUÍDO|CONCLUIDO|CANCELADO|FECHADO', regex=True, na=False)].copy()
                ineps_com_chamado = df_os_abertos['INEP'].dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()
                
                mask_tem_chamado = df_validos['INEP_Extraido'].isin(ineps_com_chamado)
                df_falta_abrir = df_validos[~mask_tem_chamado].copy()
                df_ja_aberto = df_validos[mask_tem_chamado].copy()
                
                # --- NOVA REGRA 4 HORAS OFFLINE PARA FALTA_ABRIR_CHAMADO ---
                dt_todos = pd.to_datetime(df_new[status_new].astype(str).str.extract(r'(?i)Uptime:\s*(.*)')[0], errors='coerce')
                ref_time = dt_todos.max()
                if pd.isna(ref_time):
                    ref_time = pd.Timestamp.now()
                
                def avaliar_regra_4h(val_status):
                    dt_str = pd.Series([str(val_status)]).str.extract(r'(?i)Uptime:\s*(.*)')[0].iloc[0]
                    dt_off = pd.to_datetime(dt_str, errors='coerce')
                    if pd.isna(dt_off):
                        return "⚠️ Verificar tempo offline"
                    diff_hours = (ref_time - dt_off).total_seconds() / 3600.0
                    if diff_hours < 0:
                        diff_hours = 0.0
                    h = int(diff_hours)
                    m = int(round((diff_hours - h) * 60))
                    if m == 60:
                        h += 1
                        m = 0
                    if diff_hours >= 4.0:
                        return f"✅ PODE ABRIR (>4h) - Offline há {h}h{m}m"
                    else:
                        return f"⏳ AGUARDAR (<4h) - Offline há {h}h{m}m"

                if not df_falta_abrir.empty and status_new in df_falta_abrir.columns:
                    df_falta_abrir['Regra de Abertura (4h Offline)'] = df_falta_abrir[status_new].apply(avaliar_regra_4h)
                    cols = list(df_falta_abrir.columns)
                    if 'Regra de Abertura (4h Offline)' in cols:
                        cols.remove('Regra de Abertura (4h Offline)')
                        pos = cols.index('INEP_Extraido') + 1 if 'INEP_Extraido' in cols else 1
                        cols.insert(pos, 'Regra de Abertura (4h Offline)')
                        df_falta_abrir = df_falta_abrir[cols]
                
                # NOVA LÓGICA DE FECHAR CHAMADOS: Controladoras ONLINE com chamado aberto
                cond_online = ~df_new[status_new].astype(str).str.upper().str.contains('OFFLINE')
                df_online_new = df_new[cond_online].copy()
                df_online_new['INEP_Extraido'] = df_online_new[name_new].astype(str).str.extract(r'(\d{6,})')[0]
                mask_online_com_chamado = df_online_new['INEP_Extraido'].isin(ineps_com_chamado)
                df_fechar_chamado = df_online_new[mask_online_com_chamado].copy()
                    
                # Enriquecendo OS
                df_os_abertos_unico = df_os_abertos.drop_duplicates(subset=['INEP'], keep='first')
                df_os_abertos_unico['INEP'] = df_os_abertos_unico['INEP'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                colunas_merge = [c for c in ['INEP', 'Ticket#', 'Status', 'Atribuído a'] if c in df_os_abertos_unico.columns]
                
                df_ja_aberto = df_ja_aberto.merge(df_os_abertos_unico[colunas_merge], left_on='INEP_Extraido', right_on='INEP', how='left')
                if 'INEP' in df_ja_aberto.columns: df_ja_aberto = df_ja_aberto.drop(columns=['INEP'])
                    
                if not df_fechar_chamado.empty:
                    df_fechar_chamado = df_fechar_chamado.merge(df_os_abertos_unico[colunas_merge], left_on='INEP_Extraido', right_on='INEP', how='left')
                    if 'INEP' in df_fechar_chamado.columns: df_fechar_chamado = df_fechar_chamado.drop(columns=['INEP'])

                # Enriquecimento EACE (Nome da Escola), Limpeza de Colunas e Horário de Brasília UTC-3
                escolas_eace_map = get_escolas_eace_map()
                cols_remover_omada_set = {'description', 'type', 'model', 'customer number', 'site number', 'device number', 'alert number', 'role', 'roles'}
                
                from datetime import datetime, timezone, timedelta
                fuso_br = timezone(timedelta(hours=-3))
                hora_execucao_br = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M:%S")
                
                def formatar_e_limpar(df_alvo):
                    if not isinstance(df_alvo, pd.DataFrame):
                        return df_alvo
                    # 1. Remover colunas extras do Omada (insensível a maiúsculas/minúsculas e espaços)
                    cols_drop = [c for c in df_alvo.columns if str(c).strip().lower() in cols_remover_omada_set]
                    df_alvo = df_alvo.drop(columns=cols_drop, errors='ignore')
                    
                    # 2. Inserir Nome da Escola via EACE
                    if 'INEP_Extraido' in df_alvo.columns:
                        df_alvo['Nome da Escola'] = df_alvo['INEP_Extraido'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).map(escolas_eace_map).fillna("Não Cadastrado na EACE")
                        cols = list(df_alvo.columns)
                        if 'Nome da Escola' in cols:
                            cols.remove('Nome da Escola')
                            pos = cols.index('INEP_Extraido') + 1 if 'INEP_Extraido' in cols else 1
                            cols.insert(pos, 'Nome da Escola')
                            df_alvo = df_alvo[cols]
                            
                    # 3. Adicionar coluna Atualizado Em no final
                    df_alvo['Atualizado Em'] = hora_execucao_br
                    return df_alvo

                df_falta_abrir = formatar_e_limpar(df_falta_abrir)
                df_ja_aberto = formatar_e_limpar(df_ja_aberto)
                df_fechar_chamado = formatar_e_limpar(df_fechar_chamado)
                df_ignorados = formatar_e_limpar(df_ignorados)

            st.success(f"✅ Processamento Concluído em {hora_execucao_br} (Horário de Brasília)!")
            st.info(f"🕒 A coluna **'Atualizado Em'** (`{hora_execucao_br}`) foi anexada a todos os relatórios e abas para indicar o momento exato em que o fluxo foi rodado.")
            st.divider()
            
            # --- RESULTADOS ---
            st.subheader("📊 Resultados do Fluxo Unificado")
            
            tab1, tab2, tab3, tab4 = st.tabs([
                f"🚨 Falta Abrir Chamado ({len(df_falta_abrir)})", 
                f"🎫 Já Possui Chamado ({len(df_ja_aberto)})",
                f"🟢 Fechar Chamado ({len(df_fechar_chamado)})",
                f"🚫 Ignorados - Fora RDO ({len(df_ignorados)})"
            ])
            
            with tab1:
                st.markdown("Estão Offline no Omada, constam no RDO, mas **NÃO possuem chamado**.")
                st.dataframe(df_falta_abrir, use_container_width=True)
            with tab2:
                st.markdown("Já existe um chamado ativo sendo tratado.")
                st.dataframe(df_ja_aberto, use_container_width=True)
            with tab3:
                st.markdown("Voltaram a ficar online, mas ainda possuem chamado aberto.")
                st.dataframe(df_fechar_chamado if not df_fechar_chamado.empty else pd.DataFrame(columns=['Nenhum chamado']), use_container_width=True)
            with tab4:
                st.markdown("Estão offline, mas NÃO constam no RDO.")
                st.dataframe(df_ignorados if not df_ignorados.empty else pd.DataFrame(columns=['Tudo certo']), use_container_width=True)
            
            st.divider()
            st.subheader("📥 Exportar")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if not df_falta_abrir.empty: df_falta_abrir.to_excel(writer, index=False, sheet_name='Falta_Abrir_Chamado')
                if not df_ja_aberto.empty: df_ja_aberto.to_excel(writer, index=False, sheet_name='Chamados_Abertos')
                if not df_fechar_chamado.empty: df_fechar_chamado.to_excel(writer, index=False, sheet_name='Fechar_Chamado_Recup')
                if not df_ignorados.empty: df_ignorados.to_excel(writer, index=False, sheet_name='Ignorados_Fora_do_RDO')
            
            st.download_button(
                label="📥 Baixar Relatório Completo (Excel)",
                data=output.getvalue(),
                file_name="Relatorio_Acao_Chamados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )
            
            st.divider()
            if sync_google:
                client = authenticate_gspread()
                if client:
                    with st.spinner("☁️ Sincronizando dados com o Google Sheets..."):
                        try:
                            update_gsheet_tab(client, gsheet_url, "Falta_Abrir_Chamado", df_falta_abrir)
                            update_gsheet_tab(client, gsheet_url, "Chamados_Abertos", df_ja_aberto)
                            update_gsheet_tab(client, gsheet_url, "Fechar_Chamado_Recup", df_fechar_chamado)
                            update_gsheet_tab(client, gsheet_url, "Ignorados_Fora_do_RDO", df_ignorados)
                            
                            # Sincronizar planilha completa do Omada no link dedicado do Google Sheets
                            try:
                                import unificador_auto as u_auto
                                u_auto.sincronizar_omada_google(client, omada_gsheet_url, df_new)
                                st.success(f"✅ Planilha do Omada espelhada com sucesso ({len(df_new)} controladoras)!")
                            except Exception as e_omada:
                                st.warning(f"⚠️ Erro ao espelhar planilha do Omada no Google Sheets: {e_omada}")
                                
                            st.success("✅ Planilha Google (Abas do Unificador) atualizada com sucesso! Verifique as abas online.")
                        except Exception as e_sheet:
                            st.error(f"❌ Erro ao atualizar o Google Sheets: {e_sheet}")
                else:
                    st.error("❌ Credenciais do Google não encontradas no arquivo secrets.")
            
        except Exception as e:
            st.error(f"❌ Ocorreu um erro: {str(e)}")
