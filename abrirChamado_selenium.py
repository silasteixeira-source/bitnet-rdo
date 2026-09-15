import os
import sys
import time
import json
import shutil
import logging
from datetime import datetime, timezone, timedelta

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURAÇÕES GERAIS ---
MENSAGEM_NOTA = """Olá! Sou um dos analistas do Projeto Aprender Conectado (EACE), referente à escola.

Nosso sistema detectou que nosso equipamento está sem conexão. Saberia nos informar se a escola está sem internet ou se o equipamento foi desligado?

Poderia nos enviar uma foto dos aparelhos dentro do rack preto? Assim já verificamos se há algum erro físico nas conexões.

Coletando informações com o responsável da escola."""

LOGIN_URL = "https://eace.org.br/login"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [Selenium_OS] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def init_driver():
    logging.info("Inicializando Google Chrome / Chromium via Selenium...")
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu-compositing")
    opts.add_argument("--disable-smooth-scrolling")
    opts.add_argument("--js-flags=--max-old-space-size=2048")
    opts.add_argument("--disable-setuid-sandbox")
    opts.add_argument("--window-size=1280,720")

    # Utilizando o chromedriver do sistema VPS (Debian)
    try:
        from selenium.webdriver.chrome.service import Service
        service = Service(executable_path='/usr/bin/chromedriver')
        driver = webdriver.Chrome(service=service, options=opts)
    except Exception as e:
        logging.info(f"Falha ao iniciar com Service explícito: {e}. Tentando inicialização padrão.")
        driver = webdriver.Chrome(options=opts)
        
    driver.implicitly_wait(10)
    return driver


def login_e_navegar(driver, email, password):
    try:
        logging.info(f"Acessando portal de Login: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # Aguardar os inputs renderizarem (Bubble.io pode demorar)
        for _ in range(5):
            if len(driver.find_elements(By.TAG_NAME, "input")) >= 2:
                break
            time.sleep(5)

        email_preenchido = False
        senha_preenchida = False
        
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            t = (inp.get_attribute("type") or "").lower()
            name = (inp.get_attribute("name") or "").lower()
            id_attr = (inp.get_attribute("id") or "").lower()
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            
            if not email_preenchido and (t == "email" or any(k in name or k in id_attr or k in placeholder for k in ["email", "e-mail", "user", "usuari", "login", "cpf", "cnpj"]) or (t == "text" and not email_preenchido)):
                try:
                    inp.clear()
                    inp.send_keys(email)
                    email_preenchido = True
                    logging.info(f" -> E-mail preenchido.")
                except Exception:
                    pass
            elif t == "password" and not senha_preenchida:
                try:
                    inp.clear()
                    inp.send_keys(password)
                    senha_preenchida = True
                    logging.info(" -> Senha preenchida.")
                    inp.send_keys(Keys.RETURN)
                except Exception:
                    pass
                break

        time.sleep(2)
        
        # Fallback para clicar no botão de Log In
        botoes = driver.find_elements(By.XPATH, "//button | //input[@type='submit'] | //*[@role='button'] | //a[contains(@class, 'btn')]")
        clicado = False
        for b in botoes:
            txt = (b.text or str(b.get_attribute("value") or "") or str(b.get_attribute("aria-label") or "")).strip().lower()
            if any(k in txt for k in ["log in", "login", "entrar", "acessar", "sign in"]):
                try:
                    driver.execute_script("arguments[0].click();", b)
                    clicado = True
                    logging.info(f" -> Botão de login clicado: '{txt}'")
                    break
                except Exception:
                    pass

        logging.info("Aguardando Bubble processar login (15s)...")
        time.sleep(15)
        
        # Selecionar "Fornecedor"
        logging.info("Selecionando perfil Fornecedor...")
        for el in driver.find_elements(By.XPATH, "//*[contains(text(), 'Fornecedor') or contains(text(), 'FORNECEDOR')]"):
            try:
                el.click()
                logging.info(" -> Perfil 'Fornecedor' selecionado com sucesso.")
                break
            except Exception:
                pass

        time.sleep(10)
        
        # Clicar em "Gerenciar Chamados"
        logging.info("Abrindo 'Gerenciar Chamados' (Fluxos OS)...")
        for el in driver.find_elements(By.XPATH, "//*[contains(text(), 'Gerenciar') or contains(text(), 'Chamados')]"):
            try:
                if "gerenciar" in el.text.lower() and "chamado" in el.text.lower():
                    el.click()
                    logging.info(" -> 'Gerenciar Chamados' clicado com sucesso.")
                    break
            except Exception:
                pass

        time.sleep(15)
        
        if "np_fluxos_os" in driver.current_url:
            logging.info(f"Navegação bem-sucedida! URL atual: {driver.current_url}")
            return True
        else:
            logging.error(f"Falha ao chegar em np_fluxos_os. URL atual: {driver.current_url}")
            return False

    except Exception as e:
        logging.error(f"Erro durante login e navegação: {e}")
        return False


def processar_chamados(cache_path="/app/.streamlit/snapshots/bitnet.json"):
    # --- 0. TRAVA DE SEGURANÇA: HORÁRIO COMERCIAL ---
    fuso_br = timezone(timedelta(hours=-3))
    agora = datetime.now(fuso_br)
    
    # weekday(): 0=Segunda, ..., 4=Sexta
    # Horário estrito: deve ser antes das 16h (ou seja, 08:00 até 15:59:59)
    if agora.weekday() > 4 or not (8 <= agora.hour < 16):
        logging.warning(f"ACESSO NEGADO: Fora do horário permitido (Seg-Sex, 08h às 15:59). Abortado por segurança. (Agora: {agora.strftime('%A %H:%M:%S')})")
        return

    if not os.path.exists(cache_path):
        alt_paths = ["../.streamlit/snapshots/bitnet.json", ".streamlit/snapshots/bitnet.json", "C:/Users/ADM/Documents/NOC/Arquivos/Automação/RDO/.streamlit/snapshots/bitnet.json"]
        found = False
        for alt in alt_paths:
            if os.path.exists(alt):
                cache_path = alt
                found = True
                break
        if not found:
            logging.info(f"Nenhum cache encontrado. Abortando execução.")
            return

    # --- 1. COPIAR CACHE ---
    temp_dir = os.path.join(os.getcwd(), "temp_selenium")
    os.makedirs(temp_dir, exist_ok=True)
    temp_cache_path = os.path.join(temp_dir, "bitnet_temp.json")
    
    try:
        shutil.copy2(cache_path, temp_cache_path)
    except Exception as e:
        logging.error(f"Falha ao copiar cache: {e}")
        return

    # --- 2. LER INEPs DO JSON TEMPORÁRIO (FILTRANDO) ---
    try:
        with open(temp_cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            todos_pendentes = data.get("falta_abrir", [])
            pendentes = [p for p in todos_pendentes if "CRÍTICO (>4h)" in str(p.get("Regra", ""))]
            
        if not pendentes:
            logging.info(f"Nenhum chamado crítico (>4h) encontrado na fila. Abortando.")
            return
            
        logging.info(f"Encontrados {len(pendentes)} chamados CRÍTICOS para abertura.")
    except Exception as e:
        logging.error(f"Erro ao ler JSON: {e}")
        return

    email = os.getenv("EACE_EMAIL", "noc@bitinternet.com.br")
    password = os.getenv("EACE_PASSWORD", "")
    
    driver = None
    try:
        driver = init_driver()
        sucesso = login_e_navegar(driver, email, password)
        
        if not sucesso:
            logging.error("Abortando inserção de OS devido à falha no Login/Navegação inicial.")
            return
            
        logging.info("Iniciando o loop de inserção de OS para os INEPs Críticos...")
        
        url_base_os = driver.current_url
        
        for item in pendentes:
            inep = str(item.get('INEP_Extraido', '')).strip()
            if not inep:
                continue
                
            logging.info(f"Processando INEP: {inep}")
            
            try:
                # ==============================================================================
                # ATENÇÃO: PREENCHA OS SELETORES XPATH (OU BY.CLASS_NAME / BY.CSS_SELECTOR) ABAIXO
                # ==============================================================================
                
                # Exemplo 1: Preencher a barra de pesquisa
                logging.info(f"[{inep}] Procurando barra de pesquisa...")
                input_pesquisa = driver.find_element(By.XPATH, "//input[@placeholder='Pesquisar' or contains(@placeholder, 'Buscar')]")
                input_pesquisa.clear()
                input_pesquisa.send_keys(inep)
                time.sleep(3)
                
                # Exemplo 2: Clicar no botão 'Nova OS'
                logging.info(f"[{inep}] Clicando em Nova OS...")
                btn_nova_os = driver.find_element(By.XPATH, "//*[contains(text(), 'Nova OS') or contains(text(), 'Criar OS')]")
                driver.execute_script("arguments[0].click();", btn_nova_os)
                time.sleep(3)
                
                # Exemplo 3: Preencher o modal e enviar notas
                logging.info(f"[{inep}] Preenchendo dados da OS...")
                
                # Procura o campo de inep no modal (pode precisar de ajuste)
                inputs_modal = driver.find_elements(By.XPATH, "//input[@type='text']")
                if len(inputs_modal) > 0:
                    inputs_modal[0].send_keys(inep)
                time.sleep(1)
                
                # Procura a área de texto da nota
                area_nota = driver.find_element(By.XPATH, "//textarea")
                area_nota.send_keys(MENSAGEM_NOTA)
                time.sleep(1)
                
                logging.info(f"[{inep}] Salvando OS...")
                btn_adicionar_nota = driver.find_element(By.XPATH, "//*[contains(text(), 'Adicionar Nota') or contains(text(), 'Salvar') or contains(text(), 'Enviar')]")
                driver.execute_script("arguments[0].click();", btn_adicionar_nota)
                
                logging.info(f"[{inep}] OS ABERTA COM SUCESSO!")
                
                # Retorna à tela inicial de listagem de chamados para o próximo INEP
                driver.get(url_base_os)
                time.sleep(5)
                
            except Exception as e_item:
                logging.error(f"[{inep}] Erro ao processar INEP: {e_item}")
                driver.get(url_base_os)
                time.sleep(5)
                
    except Exception as e:
        logging.error(f"Erro global na automação web: {e}")
    finally:
        if driver:
            driver.quit()
        logging.info("Automação Selenium finalizada e navegador fechado.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        processar_chamados(sys.argv[1])
    else:
        processar_chamados()
