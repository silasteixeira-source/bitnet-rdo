import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st

def get_root_dir():
    """Retorna o diretório raiz do projeto."""
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(curr_dir) == "pages":
        return os.path.dirname(curr_dir)
    return curr_dir

def get_omada_file_path():
    """Retorna o caminho da planilha gerada automaticamente pelo omada_exporter."""
    root_dir = get_root_dir()
    return os.path.join(root_dir, "omada_exporter", "dados_omada", "omada_dados.xlsx")

def get_omada_file_info():
    """
    Retorna um dicionário contendo status e metadados do arquivo exportado.
    """
    fpath = get_omada_file_path()
    exists = os.path.exists(fpath) and os.path.getsize(fpath) > 0
    if not exists:
        return {
            "exists": False,
            "path": fpath,
            "mtime": None,
            "mtime_str": "--",
            "age_minutes": None,
            "size_kb": 0
        }

    mtime = os.path.getmtime(fpath)
    dt = datetime.fromtimestamp(mtime)
    age_seconds = time.time() - mtime
    age_minutes = int(age_seconds // 60)
    size_kb = round(os.path.getsize(fpath) / 1024, 1)

    return {
        "exists": True,
        "path": fpath,
        "mtime": dt,
        "mtime_str": dt.strftime("%d/%m/%Y às %H:%M:%S"),
        "age_minutes": age_minutes,
        "size_kb": size_kb
    }

def load_omada_auto_df():
    """
    Carrega o DataFrame da planilha omada_dados.xlsx.
    """
    fpath = get_omada_file_path()
    if not os.path.exists(fpath):
        return None
    try:
        df = pd.read_excel(fpath)
        return df
    except Exception as e:
        st.error(f"Erro ao ler a planilha automática do Omada: {e}")
        return None

def render_omada_source_selector(label="Planilha OMADA", key_prefix="omada_sel"):
    """
    Exibe no Streamlit o seletor entre base automática e upload manual.
    Retorna uma tupla (origem, df_ou_file)
    - se 'auto': ('auto', df)
    - se 'manual': ('manual', uploaded_file)
    """
    info = get_omada_file_info()
    
    opcoes = []
    if info["exists"]:
        if info["age_minutes"] == 0:
            tempo_txt = "menos de 1 min atrás"
        elif info["age_minutes"] < 60:
            tempo_txt = f"{info['age_minutes']} min atrás"
        else:
            horas = info["age_minutes"] // 60
            tempo_txt = f"{horas}h atrás"
        
        opcoes.append(f"⚡ Base Automática (Atualizada em: {info['mtime_str']} — há {tempo_txt})")
    
    opcoes.append("📁 Fazer upload manual de arquivo (.xlsx)")
    
    escolha = st.radio(
        f"Selecione a origem para **{label}**:",
        options=opcoes,
        key=f"{key_prefix}_radio"
    )
    
    if "⚡ Base Automática" in escolha:
        df = load_omada_auto_df()
        return ("auto", df)
    else:
        uploaded_file = st.file_uploader(f"📁 Arquivo de {label}", type=["xlsx", "xls"], key=f"{key_prefix}_up")
        return ("manual", uploaded_file)
