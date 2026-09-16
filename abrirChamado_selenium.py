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
MENSAGEM_NOTA = """Informo que já entramos em contato com o responsável pela escola. No momento, estamos aguardando o retorno dele para que possamos entender o que ocorreu na unidade.

Assim que tivermos novas informações, farei as devidas atualizações por aqui."""

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
    # Seleção Dinâmica de Credenciais baseada no Tenant
    if "st1" in cache_path.lower():
        email = os.environ.get("EACE_ST1_EMAIL", "noceace@st1.com.br")
        senha = os.environ.get("EACE_ST1_PASSWORD", "SenhaST1Aqui")
        logging.info(f"Modo ST1 detectado. Usando credenciais de ST1: {email}")
    else:
        email = os.environ.get("EACE_EMAIL", "noc@bitinternet.com.br")
        senha = os.environ.get("EACE_PASSWORD", "EscolasConectadas@1")
        logging.info(f"Modo BITNET detectado. Usando credenciais de Bitnet: {email}")

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
        
    # As variáveis email e senha já foram definidas no topo da função baseadas no tenant!
    
    driver = None
    try:
        driver = init_driver()
        sucesso = login_e_navegar(driver, email, senha)
        
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
                # ==============================================================================
                # NOVA ROTINA DE ABERTURA DE OS (Baseada no script PyAutoGUI original)
                # ==============================================================================
                
                logging.info(f"[{inep}] 1. Filtrando OS pelo INEP na barra principal...")
                try:
                    inputs_tela = driver.find_elements(By.TAG_NAME, "input")
                    input_filtro = None
                    for inp in inputs_tela:
                        if inp.is_displayed() and str(inp.get_attribute("placeholder")).strip() == "INEP":
                            input_filtro = inp
                            break
                    
                    if input_filtro:
                        driver.execute_script("arguments[0].scrollIntoView(true);", input_filtro)
                        driver.execute_script("arguments[0].focus();", input_filtro)
                        time.sleep(0.5)
                        try: input_filtro.click()
                        except: driver.execute_script("arguments[0].click();", input_filtro)
                        input_filtro.clear()
                        input_filtro.send_keys(inep)
                        time.sleep(4) # Esperar o Kanban filtrar
                    else:
                        logging.warning(f"[{inep}] Não achei o filtro principal de INEP. Tentando seguir...")
                except Exception as e:
                    logging.error(f"[{inep}] Erro ao filtrar INEP: {e}")
                
                logging.info(f"[{inep}] 2. Clicando no botão 'Adicionar nova OS'...")
                try:
                    btn_nova_os = driver.find_element(By.XPATH, "//*[normalize-space(text())='Adicionar nova OS']")
                    driver.execute_script("arguments[0].click();", btn_nova_os)
                    time.sleep(3)
                except Exception as e:
                    logging.error(f"[{inep}] Não achei o botão 'Adicionar nova OS'. Abortando. Erro: {e}")
                    continue
                
                logging.info(f"[{inep}] 3. Preenchendo o INEP no modal de Nova OS...")
                try:
                    inputs_tela = driver.find_elements(By.TAG_NAME, "input")
                    candidatos = []
                    for inp in inputs_tela:
                        try:
                            if inp.is_displayed() and inp.get_attribute("type") in ["text", "search", ""]:
                                place = str(inp.get_attribute("placeholder") or "").strip()
                                if place in ["INEP", "OS do fornecedor", "OS da EACE"]:
                                    continue
                                candidatos.append(inp)
                        except: pass
                    
                    if not candidatos:
                        raise Exception("Não encontrei o input do modal!")
                        
                    input_escola = candidatos[-1]
                    driver.execute_script("arguments[0].focus();", input_escola)
                    time.sleep(0.5)
                    try: input_escola.click()
                    except: driver.execute_script("arguments[0].click();", input_escola)
                        
                    input_escola.clear()
                    input_escola.send_keys(inep)
                    time.sleep(4) # Mais tempo para o Bubble puxar do banco de dados
                    
                    # Precisamos CLICAR na sugestão azul que o Bubble mostra
                    try:
                        sugestoes = driver.find_elements(By.XPATH, f"//div[contains(text(), '{inep}')]")
                        clicou_sugestao = False
                        for s in sugestoes:
                            if s.is_displayed() and s.tag_name != "input":
                                driver.execute_script("arguments[0].click();", s)
                                clicou_sugestao = True
                                break
                                
                        if not clicou_sugestao:
                            input_escola.send_keys(Keys.ARROW_DOWN)
                            time.sleep(1)
                            input_escola.send_keys(Keys.ENTER)
                    except:
                        input_escola.send_keys(Keys.ENTER)
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logging.error(f"[{inep}] Erro ao digitar INEP no modal: {e}")
                    try: driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//*[text()='Fechar']"))
                    except: pass
                    continue
                
                logging.info(f"[{inep}] 4. Clicando em 'Incluir'...")
                try:
                    btn_incluir = driver.find_element(By.XPATH, "//*[normalize-space(text())='Incluir']")
                    driver.execute_script("arguments[0].click();", btn_incluir)
                    time.sleep(6) # Esperar a OS ser criada e aparecer no painel
                except Exception as e:
                    logging.error(f"[{inep}] Erro ao clicar em Incluir: {e}")
                    continue
                    
                logging.info(f"[{inep}] 5. Entrando na OS criada...")
                try:
                    # Como filtramos pelo INEP no passo 1, o card da nova OS vai ser um dos primeiros/únicos na tela
                    cards = driver.find_elements(By.XPATH, f"//*[contains(text(), '{inep}')]")
                    card_alvo = None
                    # Procurar um card clicável que não seja o próprio filtro
                    for c in cards:
                        if c.is_displayed() and c.tag_name not in ["input", "textarea"]:
                            card_alvo = c
                            break
                            
                    if card_alvo:
                        driver.execute_script("arguments[0].click();", card_alvo)
                        time.sleep(5) # Esperar OS abrir
                    else:
                        raise Exception("Card da OS não apareceu na tela principal!")
                except Exception as e:
                    logging.error(f"[{inep}] Erro ao tentar entrar na OS recém-criada: {e}")
                    continue
                
                logging.info(f"[{inep}] 6. Navegando para Notas...")
                try:
                    # Busca ampla por elementos que contenham 'Nota' (evitando 'Notas técnicas')
                    # Ao inverter a lista, garantimos que clicamos no elemento filho (o texto em si) antes do container pai!
                    elementos_nota = driver.find_elements(By.XPATH, "//*[contains(text(), 'Nota') or contains(text(), 'Anota') or text()='Nota']")
                    clicou_aba = False
                    
                    for el in reversed(elementos_nota):
                        texto_el = (el.text or el.get_attribute("innerText") or el.get_attribute("textContent") or "").strip().lower()
                        if "técnica" in texto_el or not texto_el:
                            continue
                            
                        # Removida a checagem de is_displayed() pois o Bubble esconde elementos via CSS
                        try:
                            driver.execute_script("arguments[0].click();", el)
                            clicou_aba = True
                            break # Achou o filho mais profundo e clicou
                        except: pass
                            
                    if not clicou_aba:
                        logging.warning(f"[{inep}] Não encontrei a aba 'Nota' clicável por XPath normal. Tentando forçar clique...")
                        try:
                            # Tenta clicar no rádio adjacente ou label
                            aba = driver.find_element(By.XPATH, "//label[contains(., 'Nota')]")
                            driver.execute_script("arguments[0].click();", aba)
                            clicou_aba = True
                        except: pass
                    
                    time.sleep(3)
                except Exception as e:
                    logging.warning(f"[{inep}] Erro ao buscar aba 'Nota': {e}")
                
                logging.info(f"[{inep}] 7. Preenchendo MENSAGEM_NOTA...")
                try:
                    # Tenta agressivamente pelo placeholder (funciona pra input, textarea e editores Rich Text)
                    area_nota = None
                    try:
                        area_nota = driver.find_element(By.XPATH, "//*[contains(@placeholder, 'aconteceu') or contains(@data-placeholder, 'aconteceu')]")
                    except:
                        pass
                        
                    if not area_nota:
                        # Fallback textarea
                        textareas = driver.find_elements(By.TAG_NAME, "textarea")
                        for ta in textareas:
                            if ta.is_displayed():
                                area_nota = ta
                                break
                                
                    if not area_nota:
                        # Fallback contenteditable
                        divs_editaveis = driver.find_elements(By.XPATH, "//div[@contenteditable='true']")
                        for div in divs_editaveis:
                            if div.is_displayed():
                                area_nota = div
                                break

                    if not area_nota:
                        raise Exception("A área de texto (textarea/input) da nota não foi encontrada ou não está visível.")

                    driver.execute_script("arguments[0].focus();", area_nota)
                    time.sleep(0.5)
                    try: area_nota.click()
                    except: driver.execute_script("arguments[0].click();", area_nota)
                    
                    area_nota.clear()
                    area_nota.send_keys(MENSAGEM_NOTA)
                    time.sleep(2)
                    
                    logging.info(f"[{inep}] 8. Clicando em Salvar/Adicionar Nota...")
                    botoes_adicionar = driver.find_elements(By.XPATH, "//*[contains(text(), 'Adicionar')]")
                    for btn in botoes_adicionar:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            break
                    time.sleep(4)
                    
                    sucesso_nota = True
                except Exception as e:
                    logging.error(f"[{inep}] ❌ Falha: Não encontrei a área de Notas ou botão Salvar. Erro: {e}")
                    # --- MODO RADAR REATIVADO: SALVANDO NA PASTA TEMP ---
                    try:
                        os.makedirs("/app/temp", exist_ok=True)
                        with open(f"/app/temp/erro_radar_{inep}.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        logging.error(f"[{inep}] 📡 MODO RADAR ATIVADO: HTML da tela salvo em '/app/temp/erro_radar_{inep}.html'")
                    except: pass
                    sucesso_nota = False
                    
                logging.info(f"[{inep}] 9. Fechando/Voltando da OS...")
                try:
                    # O botão de voltar fica lá no topo esquerdo "<- Voltar"
                    btn_voltar = driver.find_element(By.XPATH, "//*[contains(text(), 'Voltar')]")
                    driver.execute_script("arguments[0].click();", btn_voltar)
                    time.sleep(3)
                except:
                    pass
                    
                if sucesso_nota:
                    logging.info(f"[{inep}] ✅ OS ABERTA E NOTA INSERIDA COM SUCESSO!")
                else:
                    logging.warning(f"[{inep}] ⚠️ Ciclo finalizado, mas houve erros na nota ou abertura.")

                
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
