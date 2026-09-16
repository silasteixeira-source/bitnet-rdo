import streamlit as st
import json
import os

st.set_page_config(page_title="Configurações do Robô", page_icon="⚙️", layout="wide")
st.title("⚙️ Configurações do Robô de OS")

config_path = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "config_robo.json")

def load_config():
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar configurações: {e}")
    return {"bitnet": {"abrir_os": True, "inserir_nota": True}, "st1": {"abrir_os": True, "inserir_nota": True}}

def save_config(config):
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

config = load_config()

st.markdown("""
Esta página permite ligar ou desligar as funções autônomas do robô em tempo real.
As alterações salvas aqui entrarão em vigor no próximo ciclo de execução (a cada 3-4 minutos).
""")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("🏢 BITNET")
    with st.container(border=True):
        bitnet_abrir = st.toggle("🤖 Permitir Abertura Automática de OS", value=config.get("bitnet", {}).get("abrir_os", True), key="bitnet_os")
        st.caption("Se desativado, o robô ignorará a fila da Bitnet e não abrirá chamados novos.")
        
        st.write("")
        bitnet_nota = st.toggle("📝 Permitir Inserção de Notas nas OSs", value=config.get("bitnet", {}).get("inserir_nota", True), key="bitnet_nota")
        st.caption("Se desativado, o robô abrirá o chamado (se permitido acima), mas pulará a etapa de preencher notas.")

with col2:
    st.subheader("🏢 ST1")
    with st.container(border=True):
        st1_abrir = st.toggle("🤖 Permitir Abertura Automática de OS", value=config.get("st1", {}).get("abrir_os", True), key="st1_os")
        st.caption("Se desativado, o robô ignorará a fila da ST1 e não abrirá chamados novos.")
        
        st.write("")
        st1_nota = st.toggle("📝 Permitir Inserção de Notas nas OSs", value=config.get("st1", {}).get("inserir_nota", True), key="st1_nota")
        st.caption("Se desativado, o robô abrirá o chamado (se permitido acima), mas pulará a etapa de preencher notas.")

st.divider()

if st.button("💾 Salvar Configurações", type="primary", use_container_width=True):
    config["bitnet"] = {
        "abrir_os": bitnet_abrir,
        "inserir_nota": bitnet_nota
    }
    config["st1"] = {
        "abrir_os": st1_abrir,
        "inserir_nota": st1_nota
    }
    save_config(config)
    st.success("✅ Configurações salvas com sucesso! O robô lerá essas regras na próxima rodada.")
