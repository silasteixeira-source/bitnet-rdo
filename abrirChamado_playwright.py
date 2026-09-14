import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError
import time

# --- CONFIGURAÇÕES GERAIS ---
ARQUIVO_PLANILHA = "Chamados Pendentes (PA e MA) - Aprovados e Offline 2.xlsx"
URL_SISTEMA = "https://COLOQUE_A_URL_AQUI.com" # TODO: Coloque o link do sistema NOC aqui

MENSAGEM_NOTA = """Olá! Sou um dos analistas do Projeto Aprender Conectado (EACE), referente à escola.

Nosso sistema detectou que nosso equipamento está sem conexão. Saberia nos informar se a escola está sem internet ou se o equipamento foi desligado?

Poderia nos enviar uma foto dos aparelhos dentro do rack preto? Assim já verificamos se há algum erro físico nas conexões.

Coletando informações com o responsável da escola."""
LIMITE_DIARIO = 30

def processar_chamados():
    # --- 1. LEITURA DA PLANILHA ---
    try:
        df = pd.read_excel(ARQUIVO_PLANILHA)
    except FileNotFoundError:
        print(f"Erro: Arquivo {ARQUIVO_PLANILHA} não encontrado.")
        return

    if 'Status_Automacao' not in df.columns:
        df['Status_Automacao'] = ""

    pendentes = df[df['Status_Automacao'] == ""].head(LIMITE_DIARIO)

    if pendentes.empty:
        print("Todos os INEPs da planilha já possuem status definido!")
        return

    # --- 2. INÍCIO DA AUTOMAÇÃO WEB COM PLAYWRIGHT ---
    with sync_playwright() as p:
        print("Iniciando o navegador...")
        
        # O "user_data_dir" cria uma pasta para salvar os cookies e a sessão.
        # Assim, você não precisa fazer login toda vez que rodar o script!
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./dados_navegador", 
            headless=False, # Mantém False para você ver o robô trabalhando
            slow_mo=800     # Atrasa um pouco as ações para imitar um humano e dar tempo de vermos
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto(URL_SISTEMA)
        
        # Opcional: Pausa inicial caso você precise logar na primeira vez que rodar
        print("Aguardando carregamento da página inicial... (Se precisar, faça o login)")
        # page.wait_for_timeout(5000)
        
        # --- LOOP DE PROCESSAMENTO ---
        for index, row in pendentes.iterrows():
            inep = str(row['INEP']).strip()
            print(f"\nProcessando INEP: {inep}")
            
            try:
                # ----------------------------------------------------------------------
                # ATENÇÃO: Os seletores abaixo ("input#search", "button", etc) são apenas 
                # exemplos! Você precisará clicar com o botão direito nos elementos reais
                # do seu sistema, ir em "Inspecionar" e copiar os seletores corretos.
                # ----------------------------------------------------------------------

                # 1. Pesquisar na barra principal
                # Substitua pelo seletor CSS correto da barra de pesquisa
                seletor_pesquisa = "input[placeholder='Pesquisar']" 
                page.fill(seletor_pesquisa, inep)
                
                # 2. Clicar na opção do INEP (Exemplo usando texto)
                # O Playwright consegue achar elementos pelo texto visível!
                page.click(f"text={inep}")
                
                # 3. Adicionar Nova OS
                page.click("button:has-text('Nova OS')") 
                
                # 4. ABRIR OS - Preencher INEP no modal
                # O Playwright já tem "Auto-Wait" (Espera Inteligente). 
                # Ele vai aguardar automaticamente o modal aparecer sem precisar de time.sleep!
                seletor_modal_inep = "input#campo_inep_modal"
                page.wait_for_selector(seletor_modal_inep, state="visible")
                page.fill(seletor_modal_inep, inep)
                
                # Se após digitar precisar dar Enter ou clicar na opção que desce:
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                
                # 5. Clicar em "Incluir"
                page.click("button:has-text('Incluir')")
                
                # 6. Entrar na OS
                page.click("button:has-text('Entrar')")
                
                # 7. Clicar em "Notas"
                page.click("a:has-text('Notas')")
                
                # 8. Colar notas
                seletor_notas = "textarea#campo_notas"
                page.fill(seletor_notas, MENSAGEM_NOTA)
                
                # 9. Adicionar para finalizar
                page.click("button:has-text('Adicionar Nota')")
                
                # Dá um pequeno tempo antes de considerar sucesso
                page.wait_for_timeout(2000)
                
                # Salva o status de sucesso
                df.at[index, 'Status_Automacao'] = "OS Aberta e Nota Inserida"
                print(f"[{inep}] Sucesso!")
                
                # 10. Voltar (se necessário) e Atualizar a página
                page.go_back()
                page.reload()
                
            except TimeoutError as e:
                # O TimeoutError ocorre se o Playwright esperar 30 segundos e não achar um botão/campo
                print(f"[{inep}] Erro: A página demorou muito ou um botão não foi encontrado.")
                df.at[index, 'Status_Automacao'] = "Erro de Elemento/Timeout"
                
                # Volta para a home para não quebrar o loop no próximo INEP
                page.goto(URL_SISTEMA) 
                
            except Exception as e:
                print(f"[{inep}] Erro inesperado: {e}")
                df.at[index, 'Status_Automacao'] = f"Erro: {str(e)[:50]}"
                page.goto(URL_SISTEMA)
        
        # Fecha o navegador no final
        browser.close()
        
    # --- 3. SALVA RESULTADOS ---
    df.to_excel(ARQUIVO_PLANILHA, index=False)
    print("\nFinalizado! Planilha salva.")

if __name__ == "__main__":
    processar_chamados()
