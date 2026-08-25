#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
unificador_auto.py - Automação do Unificador de Chamados (Omada, OS e RDO)
Sem necessidade de upload via Streamlit. Roda em modo CLI / contínuo na VPS.
"""

import os
import time
import argparse
from datetime import datetime, timezone, timedelta
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Fuso horário oficial de Brasília (UTC-3)
FUSO_BR = timezone(timedelta(hours=-3))

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# URLs padrões do Google Sheets (aba 4 do Streamlit)
DEFAULT_BITNET_URL = "https://docs.google.com/spreadsheets/d/167LUrFFBJBlQ-Jh7cX717r32F2c8tfq1zsx_0FIC0WY/edit"
DEFAULT_ST1_URL = "https://docs.google.com/spreadsheets/d/1jMc7SW8ECb49j1LP8W879Xz-wyxudkkMYCH9s7nKVdU/edit"
DEFAULT_OMADA_GSHEET_URL = "https://docs.google.com/spreadsheets/d/1r8jQ8jJGWSLQoACVoBy8emYlk3avJOuEXM10W_tlY-o/edit?gid=998874036#gid=998874036"

def log(msg):
    ts = datetime.now(FUSO_BR).strftime("%Y-%m-%d %H:%M:%S")
    try:
        print(f"[{ts}] [Unificador Auto] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}] [Unificador Auto] " + msg.encode("ascii", "replace").decode("ascii"), flush=True)

def get_gspread_client():
    """Autentica no Google Sheets via segredos do Streamlit (.streamlit/secrets.toml) ou arquivo JSON."""
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            return gspread.authorize(creds)
    except Exception as e:
        log(f"Aviso: Não foi possível carregar credenciais do Streamlit ({e}).")

    # Tentativa alternativa via variável de ambiente
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/secrets.json")
    if os.path.exists(creds_path):
        try:
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
            return gspread.authorize(creds)
        except Exception as e:
            log(f"Aviso: Falha na autenticação via arquivo JSON ({e}).")
    return None

def get_escolas_eace_map(client):
    """Busca o mapeamento de código INEP -> Nome da Escola do Google Sheets."""
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
        log(f"Aviso ao buscar mapeamento EACE: {e}")
    return {}

def update_gsheet_tab(client, spreadsheet_url, sheet_name, df):
    """Atualiza ou cria a aba especificada no Google Sheets."""
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

def sincronizar_omada_google(client, url_omada, df_omada):
    """Atualiza a planilha completa do Omada no Google Sheets."""
    if not client:
        log("❌ Cliente GSpread não autenticado. Sincronização do Omada abortada.")
        return
    log(f"Sincronizando planilha completa do Omada com o Google Sheets: {url_omada}")
    try:
        sheet = client.open_by_url(url_omada)
        try:
            ws = sheet.get_worksheet_by_id(998874036)
            if not ws:
                ws = sheet.sheet1
        except Exception:
            ws = sheet.sheet1
        
        ws.clear()
        df_clean = df_omada.drop(columns=['NOME_CLEAN'], errors='ignore')
        if not df_clean.empty:
            df_str = df_clean.fillna("").astype(str)
            ws.update([df_str.columns.values.tolist()] + df_str.values.tolist())
        else:
            ws.update([["Nenhum dado encontrado"]])
        log(f"✅ Planilha completa do Omada sincronizada no Google Sheets ({len(df_clean)} controladoras)!")
    except Exception as e:
        log(f"❌ Erro ao atualizar planilha do Omada no Google Sheets: {e}")

def carregar_rdo(rdo_input, client):
    """Carrega a planilha RDO a partir de URL do Google Sheets/Drive (suporta planilhas nativas e arquivos Excel .xlsx no Drive) ou arquivo Excel local."""
    if str(rdo_input).startswith("http://") or str(rdo_input).startswith("https://"):
        log(f"Carregando RDO direto do Google Sheets/Drive: {rdo_input}")
        if not client:
            raise ValueError("Cliente GSpread não autenticado para ler RDO do Google Sheets.")
        
        # 1. Tentar como planilha nativa do Google Sheets via gspread
        try:
            sheet = client.open_by_url(rdo_input)
            try:
                ws = sheet.get_worksheet_by_id(1631182129)
                if not ws:
                    ws = sheet.sheet1
            except Exception:
                ws = sheet.sheet1
            data = ws.get_all_values()
            if len(data) > 1:
                df_rdo = pd.DataFrame(data[1:], columns=data[0])
            else:
                df_rdo = pd.DataFrame()
            return df_rdo
        except Exception as e_sheet:
            log(f"Aviso: Não foi possível ler como planilha nativa ({e_sheet}). Tentando via Google Drive API para arquivos Excel (.xlsx)...")
            # 2. Tentar como arquivo Excel (.xlsx) hospedado no Google Drive via API Drive v3
            try:
                import re
                import io
                import requests
                import google.auth.transport.requests
                
                # Extrair ID do arquivo da URL do Google Drive / Sheets
                match = re.search(r'/d/([a-zA-Z0-9_-]+)', rdo_input)
                if not match:
                    raise ValueError("ID do arquivo Google Drive não encontrado na URL.")
                file_id = match.group(1)
                
                # Atualizar token OAuth da credencial autenticada
                req_auth = google.auth.transport.requests.Request()
                client.http_client.auth.refresh(req_auth)
                token = client.http_client.auth.token
                
                url_drive = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
                headers = {"Authorization": f"Bearer {token}"}
                res = requests.get(url_drive, headers=headers)
                if res.status_code == 200:
                    df_rdo = pd.read_excel(io.BytesIO(res.content))
                    log(f"SUCESSO: RDO carregada via Google Drive API ({len(df_rdo)} linhas).")
                    return df_rdo
                else:
                    raise ValueError(f"Google Drive API retornou status {res.status_code}: {res.text}")
            except Exception as e_drive:
                raise RuntimeError(f"Falha ao carregar planilha RDO via Sheets API ({e_sheet}) e via Drive API ({e_drive})")
    else:
        log(f"Carregando RDO de arquivo Excel local: {rdo_input}")
        return pd.read_excel(rdo_input)

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
    # ascending=True para priorizar os que caíram há mais tempo (datas mais antigas no topo)
    df = df.sort_values(by='_temp_date', ascending=True).drop(columns=['_temp_date'])
    return df

def processar_fluxo(omada_old_path, omada_new_path, os_path, rdo_path, sync_google=True, gsheet_url=DEFAULT_BITNET_URL, omada_gsheet_url=DEFAULT_OMADA_GSHEET_URL, tenant="bitnet"):
    """Executa o cruzamento completo de dados e publica nas abas do Google Sheets e salva JSON."""
    log("=== Iniciando Processamento do Unificador de Chamados ===")
    
    # Se a planilha do Omada Anterior ainda não existir (primeiro ciclo), usa a Atual como fallback
    if not os.path.exists(omada_old_path) and os.path.exists(omada_new_path):
        log(f"AVISO: '{omada_old_path}' ainda não foi gerada pelo Omada Exporter. Usando a planilha atual como fallback temporário.")
        omada_old_path = omada_new_path

    # Validação da existência das planilhas (ignora checagem local se for URL http/https)
    for path, nome in [
        (omada_old_path, "Omada Anterior"),
        (omada_new_path, "Omada Atual"),
        (os_path, "Controle de OS (EACE)"),
        (rdo_path, "RDO")
    ]:
        if not str(path).startswith("http") and not os.path.exists(path):
            log(f"FALHA: Planilha ausente - {nome}: '{path}'")
            return False

    client = get_gspread_client()

    log("1/4 - Carregando e cruzando planilhas do Omada...")
    df_old = pd.read_excel(omada_old_path)
    df_new = pd.read_excel(omada_new_path)
    
    df_off_old, name_old, status_old = get_offline_controllers(df_old)
    df_off_new, name_new, status_new = get_offline_controllers(df_new)
    
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
    
    df_offline = pd.concat([df_novas, df_ainda], ignore_index=True)
    df_offline['INEP_Extraido'] = df_offline[name_new].astype(str).str.extract(r'(\d{6,})')[0]
    if not df_recuperadas.empty:
        df_recuperadas['INEP_Extraido'] = df_recuperadas[name_old].astype(str).str.extract(r'(\d{6,})')[0]

    # --- FILTRO ANTI-FALSO-OFFLINE E DEDUPLICAÇÃO DE INEPs ---
    # 1. Identifica qualquer INEP que possua pelo menos uma controladora ONLINE no Omada Atual
    df_online_tmp = df_new[~df_new[status_new].astype(str).str.upper().str.contains('OFFLINE', na=False)].copy()
    df_online_tmp['INEP_Extraido'] = df_online_tmp[name_new].astype(str).str.extract(r'(\d{6,})')[0]
    ineps_online_now = set(df_online_tmp['INEP_Extraido'].dropna().astype(str).str.strip())
    
    # 2. Exclui de df_offline qualquer controladora offline cujo INEP já esteja ONLINE (ex: OC200 antiga inativa no cloud)
    inep_series_off = df_offline['INEP_Extraido'].astype(str).str.strip()
    removidos_online = df_offline[inep_series_off.isin(ineps_online_now)]
    if not removidos_online.empty:
        log(f"⚡ Filtro Anti-Falso-Offline: {len(removidos_online)} controladoras offline ignoradas porque o INEP já está ONLINE no Omada (ex: {list(removidos_online['INEP_Extraido'].unique())[:5]}).")
    df_offline = df_offline[~inep_series_off.isin(ineps_online_now)].copy()

    # 3. Deduplica df_offline por INEP_Extraido (caso exista mais de 1 controladora offline para o mesmo INEP)
    df_offline = df_offline.drop_duplicates(subset=['INEP_Extraido'], keep='first').copy()

    log("2/4 - Validando INEPs contra a planilha RDO...")
    df_rdo = carregar_rdo(rdo_path, client)
    if 'INEP' in df_rdo.columns:
        serie_inep = df_rdo['INEP']
    elif df_rdo.shape[1] > 12:
        serie_inep = df_rdo.iloc[:, 12]
    else:
        raise ValueError("A planilha RDO não possui coluna nomeada 'INEP' ou coluna 12 (M).")
        
    ineps_rdo = serie_inep.dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()
    mask_no_rdo = df_offline['INEP_Extraido'].isin(ineps_rdo)
    df_validos = df_offline[mask_no_rdo].copy()
    df_ignorados = df_offline[~mask_no_rdo].copy()

    log("3/4 - Cruzando com Controle de OS (EACE)...")
    df_os = pd.read_excel(os_path)
    df_os_abertos = df_os[~df_os['Status'].astype(str).str.upper().str.contains('CONCLUÍDO|CONCLUIDO|CANCELADO|FECHADO', regex=True, na=False)].copy()
    ineps_com_chamado = df_os_abertos['INEP'].dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()
    
    mask_tem_chamado = df_validos['INEP_Extraido'].isin(ineps_com_chamado)
    df_falta_abrir = df_validos[~mask_tem_chamado].copy()
    df_ja_aberto = df_validos[mask_tem_chamado].copy()

    # Avaliando Regra de Abertura (4 horas offline)
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
        if diff_hours >= 12.0:
            return f"🚨 CRÍTICO (>12h) - Offline há {h}h{m}m"
        elif diff_hours >= 4.0:
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

    # Fechar chamados recup
    cond_online = ~df_new[status_new].astype(str).str.upper().str.contains('OFFLINE')
    df_online_new = df_new[cond_online].copy()
    df_online_new['INEP_Extraido'] = df_online_new[name_new].astype(str).str.extract(r'(\d{6,})')[0]
    mask_online_com_chamado = df_online_new['INEP_Extraido'].isin(ineps_com_chamado)
    df_fechar_chamado = df_online_new[mask_online_com_chamado].copy()

    # Merge com detalhes da OS
    df_os_abertos_unico = df_os_abertos.drop_duplicates(subset=['INEP'], keep='first')
    df_os_abertos_unico['INEP'] = df_os_abertos_unico['INEP'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    colunas_merge = [c for c in ['INEP', 'Ticket#', 'Status', 'Atribuído a'] if c in df_os_abertos_unico.columns]
    
    df_ja_aberto = df_ja_aberto.merge(df_os_abertos_unico[colunas_merge], left_on='INEP_Extraido', right_on='INEP', how='left')
    if 'INEP' in df_ja_aberto.columns: df_ja_aberto = df_ja_aberto.drop(columns=['INEP'])
        
    if not df_fechar_chamado.empty:
        df_fechar_chamado = df_fechar_chamado.merge(df_os_abertos_unico[colunas_merge], left_on='INEP_Extraido', right_on='INEP', how='left')
        if 'INEP' in df_fechar_chamado.columns: df_fechar_chamado = df_fechar_chamado.drop(columns=['INEP'])

    log("4/4 - Enriquecendo relatórios e atualizando Google Sheets...")
    client = get_gspread_client()
    escolas_eace_map = get_escolas_eace_map(client)
    cols_remover_omada_set = {'description', 'type', 'model', 'customer number', 'site number', 'device number', 'alert number', 'role', 'roles'}
    
    hora_execucao_br = datetime.now(FUSO_BR).strftime("%d/%m/%Y %H:%M:%S")
    
    def formatar_e_limpar(df_alvo):
        if not isinstance(df_alvo, pd.DataFrame):
            return df_alvo
        cols_drop = [c for c in df_alvo.columns if str(c).strip().lower() in cols_remover_omada_set]
        df_alvo = df_alvo.drop(columns=cols_drop, errors='ignore')
        
        if 'INEP_Extraido' in df_alvo.columns:
            df_alvo['Nome da Escola'] = df_alvo['INEP_Extraido'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).map(escolas_eace_map).fillna("Não Cadastrado na EACE")
            cols = list(df_alvo.columns)
            if 'Nome da Escola' in cols:
                cols.remove('Nome da Escola')
                pos = cols.index('INEP_Extraido') + 1 if 'INEP_Extraido' in cols else 1
                cols.insert(pos, 'Nome da Escola')
                df_alvo = df_alvo[cols]
                
        df_alvo['Atualizado Em'] = hora_execucao_br
        return df_alvo.fillna("")

    df_falta_abrir = formatar_e_limpar(df_falta_abrir)
    df_ja_aberto = formatar_e_limpar(df_ja_aberto)
    df_fechar_chamado = formatar_e_limpar(df_fechar_chamado)
    df_ignorados = formatar_e_limpar(df_ignorados)
    
    # NOVO: Separar os 'Não Cadastrado na EACE' da fila principal de Falta Abrir
    if 'Nome da Escola' in df_falta_abrir.columns:
        mask_nao_cad = df_falta_abrir['Nome da Escola'] == "Não Cadastrado na EACE"
        df_nao_cadastrado = df_falta_abrir[mask_nao_cad].copy()
        df_falta_abrir = df_falta_abrir[~mask_nao_cad].copy()
    else:
        df_nao_cadastrado = pd.DataFrame()

    log(f"Resultados calculados -> Falta Abrir: {len(df_falta_abrir)} | Não Cadastrados: {len(df_nao_cadastrado)} | Já Possui: {len(df_ja_aberto)} | Fechar: {len(df_fechar_chamado)} | Ignorados: {len(df_ignorados)}")

    # NOVO: Salvar JSON Snapshot
    snapshot_dir = "/app/.streamlit/snapshots"
    if not os.path.exists("/app/.streamlit"):
        snapshot_dir = "../.streamlit/snapshots" if os.path.exists("../.streamlit") else ".streamlit/snapshots"
    
    os.makedirs(snapshot_dir, exist_ok=True)
    snapshot_path = os.path.join(snapshot_dir, f"{tenant}.json")
    
    snapshot_data = {
        "falta_abrir": df_falta_abrir.to_dict(orient='records'),
        "abertos": df_ja_aberto.to_dict(orient='records'),
        "fechar": df_fechar_chamado.to_dict(orient='records'),
        "updated_at": hora_execucao_br
    }
    
    import json
    try:
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_data, f, ensure_ascii=False, indent=2)
        log(f"✅ Snapshot JSON salvo para o tenant {tenant} em: {snapshot_path}")
    except Exception as e:
        log(f"❌ Erro ao salvar snapshot JSON: {e}")

    if sync_google and client:
        log(f"Sincronizando com o Google Sheets: {gsheet_url}")
        try:
            update_gsheet_tab(client, gsheet_url, "Falta_Abrir_Chamado", df_falta_abrir)
            update_gsheet_tab(client, gsheet_url, "Chamados_Abertos", df_ja_aberto)
            update_gsheet_tab(client, gsheet_url, "Fechar_Chamado_Recup", df_fechar_chamado)
            update_gsheet_tab(client, gsheet_url, "Nao_Cadastrados_EACE", df_nao_cadastrado)
            update_gsheet_tab(client, gsheet_url, "Ignorados_Fora_do_RDO", df_ignorados)
            log("✅ Sincronização Google Sheets concluída com sucesso!")
            
            # Novo: Sincronizar planilha completa do Omada no link especificado pelo usuário
            if omada_gsheet_url:
                sincronizar_omada_google(client, omada_gsheet_url, df_new)
        except Exception as e:
            log(f"❌ Erro ao atualizar o Google Sheets: {e}")
    elif sync_google and not client:
        log("❌ AVISO: Sincronização Google Sheets solicitada, mas não foi possível autenticar o cliente GSpread.")

    return True

def main():
    parser = argparse.ArgumentParser(description="Unificador Automático de Chamados (Omada, OS e RDO)")
    parser.add_argument("--old", type=str, default="omada/dados_omada/omada_dados_anterior.xlsx", help="Caminho para omada_dados_anterior.xlsx")
    parser.add_argument("--new", type=str, default="omada/dados_omada/omada_dados.xlsx", help="Caminho para omada_dados.xlsx")
    parser.add_argument("--os", type=str, default="eace/dados_eace/controle_os_ri.xlsx", help="Caminho para controle_os_ri.xlsx")
    parser.add_argument("--rdo", type=str, default="https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit?gid=1631182129#gid=1631182129", help="URL do Google Sheets do RDO ou caminho para arquivo Excel local")
    parser.add_argument("--url", type=str, default=DEFAULT_BITNET_URL, help="URL da planilha Google de destino")
    parser.add_argument("--omada-url", type=str, default=DEFAULT_OMADA_GSHEET_URL, help="URL da planilha Google do Omada")
    parser.add_argument("--tenant", type=str, default="bitnet", help="Nome do tenant (ex: bitnet, st1)")
    parser.add_argument("--no-sync", action="store_true", help="Não sincronizar com Google Sheets")
    parser.add_argument("--intervalo", type=int, default=0, help="Intervalo em segundos para repetição contínua (0 = apenas uma vez)")
    args = parser.parse_args()

    # Tenta utilizar RDO por URL ou localiza arquivo
    rdo_path = args.rdo
    if not rdo_path:
        rdo_path = "https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit?gid=1631182129#gid=1631182129"
    elif not str(rdo_path).startswith("http") and not os.path.exists(rdo_path):
        possiveis_rdo = [
            "rdo/rdo.xlsx",
            "rdoatualizado1.xlsx",
            "rdoatualizado.xlsx",
            "rdo.xlsx",
            "pages/rdoatualizado1.xlsx"
        ]
        for p in possiveis_rdo:
            if os.path.exists(p):
                rdo_path = p
                break
        if not os.path.exists(rdo_path):
            log("AVISO: Arquivo RDO local não encontrado. Usando URL oficial do Google Sheets como RDO.")
            rdo_path = "https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit?gid=1631182129#gid=1631182129"

    log(f"Origens configuradas -> Omada Anterior: {args.old} | Omada Atual: {args.new} | OS EACE: {args.os} | RDO: {rdo_path}")

    if args.intervalo > 0:
        log("⚡ Modo contínuo (Watchdog Inteligente) ativado!")
        log("O robô irá monitorar em tempo real quando o Omada Exporter (Robô 1) e o EACE Exporter (Robô 2) concluírem suas atualizações.")
        
        last_mtime_omada = 0
        last_mtime_eace = 0

        while True:
            try:
                omada_exists = os.path.exists(args.new)
                eace_exists = os.path.exists(args.os)

                if omada_exists and eace_exists:
                    mtime_omada = os.path.getmtime(args.new)
                    mtime_eace = os.path.getmtime(args.os)

                    # Se qualquer uma das planilhas foi atualizada desde a última execução
                    if mtime_omada > last_mtime_omada or mtime_eace > last_mtime_eace:
                        log("🔔 Nova exportação detectada nas planilhas do Omada e/ou Controle de OS!")
                        # Aguarda 5 segundos para garantir que o arquivo terminou de ser gravado no disco
                        time.sleep(5)
                        
                        sucesso = processar_fluxo(
                            omada_old_path=args.old,
                            omada_new_path=args.new,
                            os_path=args.os,
                            rdo_path=rdo_path,
                            sync_google=(not args.no_sync),
                            gsheet_url=args.url,
                            omada_gsheet_url=args.omada_url,
                            tenant=args.tenant
                        )
                        if sucesso:
                            last_mtime_omada = os.path.getmtime(args.new)
                            last_mtime_eace = os.path.getmtime(args.os)
                            log("✅ Cruzamento concluído! Aguardando o próximo ciclo dos robôs 1 e 2...")
                        else:
                            log("⚠️ Ocorreu um problema no cruzamento. Tentando novamente em 30s...")
                            time.sleep(30)
                            continue
                else:
                    log("⏳ Aguardando os arquivos do Omada e EACE serem criados pela primeira vez...")
            except Exception as ex:
                log(f"Erro no monitoramento do unificador: {ex}")

            # Verifica o disco a cada 15 segundos sem gastar CPU
            time.sleep(15)
    else:
        processar_fluxo(
            omada_old_path=args.old,
            omada_new_path=args.new,
            os_path=args.os,
            rdo_path=rdo_path,
            sync_google=(not args.no_sync),
            gsheet_url=args.url,
            omada_gsheet_url=args.omada_url,
            tenant=args.tenant
        )

if __name__ == "__main__":
    main()
