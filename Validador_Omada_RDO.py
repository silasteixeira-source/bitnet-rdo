import streamlit as st

st.set_page_config(
    page_title="Ferramentas NOC",
    page_icon="🛠️",
    layout="wide"
)

st.write("# Bem-vindo ao Portal de Ferramentas NOC! 🛠️")

st.markdown(
    """
    Este portal contém as ferramentas desenvolvidas para automatizar e facilitar as análises diárias da equipe.
    
    👈 **Selecione a ferramenta desejada no menu lateral à esquerda:**

    - **1. Validador Omada:** Faz o cruzamento de dados e valida se as controladoras que deveriam estar online (segundo o RDO) não estão indevidamente offline no Omada.
    - **2. Comparador Omada:** Compara a evolução de status entre duas planilhas diferentes do Omada para mostrar quem caiu e quem voltou.
    - **3. Verificador de Chamados:** Cruza o relatório de Offline com o Controle de OS para saber onde já existe chamado aberto e onde falta atuar.
    """
)
