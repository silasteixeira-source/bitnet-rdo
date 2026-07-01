import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Validador OMADA x RDO", page_icon="📡", layout="wide")

st.title("📡 Validador OMADA x RDO")
st.markdown("Faça o upload das planilhas abaixo para verificar quais controladoras estão indevidamente desligadas.")

# Uploaders em colunas
col1, col2 = st.columns(2)
with col1:
    omada_file = st.file_uploader("📁 Upload da Planilha OMADA", type=["xlsx", "xls"])
with col2:
    rdo_file = st.file_uploader("📁 Upload da Planilha RDO", type=["xlsx", "xls"])

st.divider()

# Configuração de onde buscar o INEP
st.subheader("⚙️ Configurações de Leitura")
modo_coluna_inep = st.radio(
    "Como deseja identificar a coluna do INEP na planilha RDO?", 
    ["Pela posição (Coluna M)", "Pelo nome da coluna"]
)

nome_col_inep = ""
if modo_coluna_inep == "Pelo nome da coluna":
    nome_col_inep = st.text_input("Digite o nome exato da coluna (diferencia maiúsculas de minúsculas):", value="INEP")

if st.button("🚀 Analisar e Validar", type="primary", use_container_width=True):
    if not omada_file or not rdo_file:
        st.warning("⚠️ Por favor, faça o upload das duas planilhas antes de continuar.")
    else:
        try:
            with st.spinner("Analisando os dados..."):
                # 1. Carrega planilha RDO
                df_rdo = pd.read_excel(rdo_file)
                
                # Definir a coluna INEP do RDO
                if modo_coluna_inep == "Pela posição (Coluna M)":
                    # Coluna M corresponde ao índice 12 (0 é A, 1 é B...)
                    if df_rdo.shape[1] > 12:
                        serie_inep = df_rdo.iloc[:, 12]
                    else:
                        st.error("❌ A planilha RDO não possui a coluna M (ela tem menos de 13 colunas).")
                        st.stop()
                else:
                    if nome_col_inep not in df_rdo.columns:
                        st.error(f"❌ A coluna '{nome_col_inep}' não foi encontrada na planilha RDO.")
                        st.stop()
                    serie_inep = df_rdo[nome_col_inep]

                # Limpa e coleta os INEPs ativos
                ineps_ativos = serie_inep.dropna().astype(str).str.strip().str.replace(r'\.0$', '', regex=True).tolist()

                # 2. Carrega planilha OMADA
                df_omada = pd.read_excel(omada_file)

                # Busca dinâmica pelas colunas NAME e STATUS
                col_name = 'NAME' if 'NAME' in df_omada.columns else df_omada.columns[0]
                col_status = None
                for col in df_omada.columns:
                    if 'status' in str(col).lower():
                        col_status = col
                        break
                
                if col_status is None:
                    st.error("❌ A coluna 'STATUS' não foi encontrada na planilha Omada.")
                    st.stop()

                # 3. Extrai o número do INEP de dentro da coluna de Nome da Omada
                df_omada['INEP_Extraido'] = df_omada[col_name].astype(str).str.extract(r'(\d{6,})')[0]

                # 4. Filtro Lógico:
                cond_inep = df_omada['INEP_Extraido'].isin(ineps_ativos)
                cond_status = df_omada[col_status].astype(str).str.upper().str.contains('OFFLINE')

                df_resultado = df_omada[cond_inep & cond_status].copy()

                st.divider()
                st.subheader("📊 Resultados")

                if df_resultado.empty:
                    st.success("✅ Tudo Certo! Nenhuma controladora indevidamente desligada foi encontrada. Todas listadas no RDO estão online.")
                else:
                    st.error(f"⚠️ Encontradas {len(df_resultado)} controladora(s) desligada(s) que deveriam estar ativas.")
                    
                    # Formatação visual da tabela
                    colunas_exibicao = [col_name, 'INEP_Extraido', col_status]
                    if 'MODEL' in df_resultado.columns:
                        colunas_exibicao.append('MODEL')
                    
                    st.dataframe(df_resultado[colunas_exibicao], use_container_width=True)

                    # Botão para baixar o arquivo excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_resultado.to_excel(writer, index=False, sheet_name='Desligadas')
                    
                    st.download_button(
                        label="📥 Baixar Relatório em Excel",
                        data=output.getvalue(),
                        file_name="Relatorio_Controladoras_Desligadas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado ao analisar:\n{str(e)}")
