import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError
import time
import os
import shutil
import logging
import sys
import json

# --- CONFIGURAÇÕES GERAIS ---

MENSAGEM_NOTA = """Olá! Sou um dos analistas do Projeto Aprender Conectado (EACE), referente à escola.

Nosso sistema detectou que nosso equipamento está sem conexão. Saberia nos informar se a escola está sem internet ou se o equipamento foi desligado?

Poderia nos enviar uma foto dos aparelhos dentro do rack preto? Assim já verificamos se há algum erro físico nas conexões.

Coletando informações com o responsável da escola."""

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Playwright_OS] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def processar_chamados(cache_path="/app/.streamlit/snapshots/bitnet.json"):
    # --- 0. TRAVA DE SEGURANÇA: HORÁRIO COMERCIAL ---
    from datetime import datetime, timezone, timedelta
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br)
    
    # weekday(): 0=Segunda, ..., 4=Sexta
    if agora.weekday() > 4 or not (8 <= agora.hour < 17):
        logging.warning(f"ACESSO NEGADO: Fora do horário permitido (Seg-Sex, 08h às 16h). O script foi abortado por segurança. (Agora: {agora.strftime('%A %H:%M')})")
        return

    # Verifica se o cache existe
    if not os.path.exists(cache_path):
        # Fallbacks em caso de rodar localmente fora do docker
        alt_paths = ["../.streamlit/snapshots/bitnet.json", ".streamlit/snapshots/bitnet.json", "C:/Users/ADM/Documents/NOC/Arquivos/Automação/RDO/.streamlit/snapshots/bitnet.json"]
        found = False
        for alt in alt_paths:
            if os.path.exists(alt):
                cache_path = alt
                found = True
                break
        
        if not found:
            logging.info(f"Nenhum cache encontrado em {cache_path}. Abortando execução.")
            return

    # --- 1. COPIAR CACHE PARA PASTA TEMPORÁRIA ---
    temp_dir = os.path.join(os.getcwd(), "temp_playwright")
    os.makedirs(temp_dir, exist_ok=True)
    temp_cache_path = os.path.join(temp_dir, "bitnet_temp.json")
    
    try:
        shutil.copy2(cache_path, temp_cache_path)
        logging.info(f"Cache copiado para arquivo temporário: {temp_cache_path}")
    except Exception as e:
        logging.error(f"Falha ao copiar arquivo de cache: {e}")
        return

    # --- 2. LER INEPs DO JSON TEMPORÁRIO (FILTRANDO APENAS OS CRÍTICOS) ---
    try:
        with open(temp_cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Lê todos os que faltam abrir
            todos_pendentes = data.get("falta_abrir", [])
            
            # FILTRO: Apenas os que contém "🚨 CRÍTICO (>4h)" na coluna 'Regra'
            pendentes = [p for p in todos_pendentes if "CRÍTICO (>4h)" in str(p.get("Regra", ""))]
            
        if not pendentes:
            logging.info(f"Nenhum chamado crítico (>4h) encontrado na fila de {len(todos_pendentes)}. Abortando execução.")
            return
            
        logging.info(f"Encontrados {len(pendentes)} chamados CRÍTICOS para abertura.")
    except Exception as e:
        logging.error(f"Erro ao ler JSON temporário: {e}")
        return

    # --- 2.5 LER CREDENCIAIS (Mesmo padrão do eace_os_exporter) ---
    email = os.getenv("EACE_EMAIL", "noc@bitinternet.com.br")
    password = os.getenv("EACE_PASSWORD", "")
    LOGIN_URL = "https://eace.org.br/login"

    # --- 3. INÍCIO DA AUTOMAÇÃO WEB COM PLAYWRIGHT (HEADLESS/VPS) ---
    with sync_playwright() as p:
        logging.info("Iniciando o navegador em modo Headless (VPS)...")
        
        browser = p.chromium.launch_persistent_context(
            user_data_dir="./dados_navegador", 
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer"
            ]
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        # --- ETAPA DE LOGIN ---
        logging.info(f"Acessando portal de Login: {LOGIN_URL}")
        page.goto(LOGIN_URL)
        
        try:
            # Tenta logar (se já não estiver logado pela sessão persistente)
            if page.locator("input[type='email'], input[placeholder*='email']").is_visible(timeout=5000):
                logging.info("Preenchendo e-mail e senha...")
                page.fill("input[type='email'], input[placeholder*='email']", email)
                page.fill("input[type='password']", password)
                
                # Clica no botão de Log In
                page.locator("button:has-text('Log In'), button:has-text('Login'), button:has-text('Entrar')").first.click(timeout=30000)
                
                logging.info("Aguardando carregar tela de perfil... Selecionando perfil Fornecedor...")
                # O Bubble pode ser bem lento, então espera até 30s pelo perfil
                page.locator("text=/fornecedor/i").first.click(timeout=30000)
                
                logging.info("Navegando para Gerenciar Chamados...")
                page.locator("text=/gerenciar chamados/i, text=/chamados/i").first.click(timeout=30000)
                
                # Aguarda carregar a URL correta (np_fluxos_os) com timeout estendido de 60s
                page.wait_for_url("**/np_fluxos_os/**", timeout=60000)
            else:
                logging.info("Já logado (sessão aproveitada).")
                # Garante que está na URL certa
                if "np_fluxos_os" not in page.url:
                    logging.info("Navegando para tela de chamados...")
                    page.locator("text=/gerenciar chamados/i, text=/chamados/i").first.click(timeout=30000)
                    page.wait_for_url("**/np_fluxos_os/**", timeout=60000)
                    
        except TimeoutError:
            logging.error("Falha de tempo limite durante o login ou navegação inicial.")
            browser.close()
            return

        logging.info("Pronto para inserir OS. Iniciando processamento dos INEPs...")
        
        for item in pendentes:
            inep = str(item.get('INEP_Extraido', '')).strip()
            if not inep:
                continue
                
            logging.info(f"Processando INEP: {inep}")
            
            try:
                # ----------------------------------------------------------------------
                # ATENÇÃO: Os seletores abaixo ("input#search", "button", etc) são apenas 
                # exemplos! Você precisará ajustar para o seu sistema real.
                # ----------------------------------------------------------------------

                seletor_pesquisa = "input[placeholder='Pesquisar']" 
                page.fill(seletor_pesquisa, inep)
                
                page.click(f"text={inep}")
                
                page.click("button:has-text('Nova OS')") 
                
                seletor_modal_inep = "input#campo_inep_modal"
                # Usando timeout menor no modal para evitar travar 30s por INEP
                page.wait_for_selector(seletor_modal_inep, state="visible", timeout=15000)
                page.fill(seletor_modal_inep, inep)
                
                page.keyboard.press("ArrowDown")
                page.keyboard.press("Enter")
                
                page.click("button:has-text('Incluir')")
                page.click("button:has-text('Entrar')")
                page.click("a:has-text('Notas')")
                
                seletor_notas = "textarea#campo_notas"
                page.fill(seletor_notas, MENSAGEM_NOTA)
                
                page.click("button:has-text('Adicionar Nota')")
                page.wait_for_timeout(2000)
                
                logging.info(f"[{inep}] Sucesso! OS aberta e nota inserida.")
                
                page.go_back()
                page.reload()
                
            except TimeoutError as e:
                logging.error(f"[{inep}] Timeout: A página demorou muito ou elemento não foi encontrado.")
                page.goto("https://eace.org.br/np_fluxos_os")
                
            except Exception as e:
                logging.error(f"[{inep}] Erro inesperado: {e}")
                page.goto("https://eace.org.br/np_fluxos_os")
        
        browser.close()
        logging.info("Processamento finalizado. Navegador fechado.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        processar_chamados(sys.argv[1])
    else:
        processar_chamados()
