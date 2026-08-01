"""
================================================================================
  Omada Cloud Data Exporter v2.0
  Automatiza o acesso ao TP-Link Omada Cloud, realiza login com suas credenciais,
  muda a visualização para LIST, e exporta os dados em formato XLSX a cada
  intervalo configurável.
  
  O arquivo é sempre sobrescrito, servindo como base de dados atualizada.
  Interface gráfica (Tkinter) para controle do intervalo e monitoramento.
================================================================================

  Requisitos: Python 3.8+ e Selenium
  Instalação: pip install selenium
  Execução:   python omada_exporter.py

  NOTA: Na primeira execução, o Selenium baixa automaticamente o ChromeDriver
  compatível. Certifique-se de que o Google Chrome está instalado no seu PC.
"""

import os
import sys
import time
import glob
import shutil
import threading
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    tk = None
    ttk = None
    messagebox = None
    filedialog = None
    TKINTER_AVAILABLE = False
from datetime import datetime
import json
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================================
# CONSTANTES PADRÃO
# ============================================================================
DEFAULT_EMAIL = "noceace@bitinternet.com.br"
DEFAULT_PASSWORD = os.getenv("OMADA_PASSWORD", "")
DEFAULT_URL = "https://use1-omada-cloud.tplinkcloud.com/#/cloudAccessManager"
DEFAULT_INTERVAL = 30  # segundos
DEFAULT_FILENAME = "omada_dados.xlsx"


def get_default_download_dir():
    """Retorna o diretório padrão baseado na localização do script."""
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "dados_omada"
    )


# ============================================================================
# CLASSE PRINCIPAL DO EXPORTADOR
# ============================================================================
class OmadaExporter:
    """Gerencia a automação do Omada Cloud via Selenium."""

    def __init__(self, email, password, interval, download_dir, filename, eace_path=None):
        self.email = email
        self.password = password
        self.interval = interval
        self.download_dir = download_dir
        self.filename = filename
        self.eace_path = eace_path
        self.running = False
        self.driver = None
        self.export_count = 0
        self.last_export_time = None
        self.is_logged_in = False
        self.is_list_view = False
        self.on_log = None
        self.on_status = None
        
        # Sistema de rastreamento de dados processados
        self.db_path = os.path.join(self.download_dir, "processamento_status.json")
        self.general_db_path = os.path.join(self.download_dir, "planilha_geral_novos_dados.xlsx")
        self.processed_data = self._load_processed_data()
        self.inep_list = self._load_ineps_from_eace()

    def _load_processed_data(self):
        """Carrega o registro de links/INEPs já processados."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"links": {}, "ineps": {}}
        return {"links": {}, "ineps": {}}

    def _save_processed_data(self):
        """Salva o registro de links/INEPs processados."""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.processed_data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self._log(f"Erro ao salvar status de processamento: {e}")

    def _load_ineps_from_eace(self):
        """Lê os INEPs da planilha EACE se fornecida."""
        if not self.eace_path or not os.path.exists(self.eace_path):
            return []
        try:
            self._log(f"Lendo INEPs da planilha: {os.path.basename(self.eace_path)}")
            # Tentar ler Excel (precisa de openpyxl)
            df = pd.read_excel(self.eace_path)
            # Procurar por coluna que contenha 'INEP' no nome
            inep_col = [c for c in df.columns if 'INEP' in str(c).upper()]
            if inep_col:
                ineps = df[inep_col[0]].dropna().astype(str).tolist()
                self._log(f"  {len(ineps)} INEPs carregados da planilha EACE.")
                return ineps
            else:
                self._log("  AVISO: Coluna 'INEP' não encontrada na planilha EACE.")
                return []
        except Exception as e:
            self._log(f"  Erro ao ler planilha EACE: {e}")
            return []

    def _is_already_processed(self, link, inep=None):
        """Verifica se o link ou INEP já foi processado nesta sessão ou anteriormente."""
        if link in self.processed_data["links"]:
            return True
        if inep and str(inep) in self.processed_data["ineps"]:
            return True
        return False

    def _mark_as_processed(self, link, inep=None, info="", all_data=None):
        """Marca um link/INEP como concluído e atualiza a planilha geral se necessário."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. Atualizar banco de dados JSON
        self.processed_data["links"][link] = {"timestamp": ts, "info": info}
        is_new_or_unmapped = True
        
        if inep:
            inep_str = str(inep)
            self.processed_data["ineps"][inep_str] = {"timestamp": ts, "link": link}
            if inep_str in self.inep_list:
                is_new_or_unmapped = False
        
        self._save_processed_data()

        # 2. Se for um dado novo (não está na EACE) ou sem INEP, adicionar à Planilha Geral
        if is_new_or_unmapped and all_data:
            self._update_general_spreadsheet(all_data)

    def _update_general_spreadsheet(self, new_row_data):
        """Adiciona dados que não estão na EACE à planilha geral."""
        try:
            # new_row_data deve ser um dicionário com os dados da linha
            new_row_data['Data Processamento'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if os.path.exists(self.general_db_path):
                df_general = pd.read_excel(self.general_db_path)
                # Evitar duplicatas na planilha geral baseada no link
                if 'Link' in df_general.columns and new_row_data.get('Link') in df_general['Link'].values:
                    return
                df_new = pd.DataFrame([new_row_data])
                df_combined = pd.concat([df_general, df_new], ignore_index=True)
                df_combined.to_excel(self.general_db_path, index=False)
            else:
                df_new = pd.DataFrame([new_row_data])
                df_new.to_excel(self.general_db_path, index=False)
            
            self._log(f"  Dado novo registrado na Planilha Geral: {new_row_data.get('Link', 'N/A')}")
        except Exception as e:
            self._log(f"  Erro ao atualizar planilha geral: {e}")

    # -----------------------------------------------------------------------
    # UTILITÁRIOS
    # -----------------------------------------------------------------------
    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        text = f"[{ts}] {msg}"
        if self.on_log:
            self.on_log(text)
        else:
            print(text) # Log para console em modo CLI

    def _set_status(self, text):
        if self.on_status:
            self.on_status(text)
        else:
            self._log(f"STATUS: {text}") # Log para console em modo CLI

    def _wait(self, seconds):
        """Aguarda respeitando o flag de parada."""
        end = time.time() + seconds
        while time.time() < end and self.running:
            time.sleep(0.3)

    # -----------------------------------------------------------------------
    # DRIVER
    # -----------------------------------------------------------------------
    def _create_driver(self):
        """Cria e configura o ChromeDriver."""

        opts = Options()
        opts.add_argument("--disable-extensions")
        opts.add_argument("--ignore-certificate-errors")
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--remote-debugging-pipe")
        opts.add_argument("--remote-allow-origins=*")
        opts.add_argument("--js-flags=--max-old-space-size=512")
        opts.add_argument("--disable-site-isolation-trials")
        opts.add_argument("--disable-features=IsolateOrigins,site-per-process,Translate,BackForwardCache")
        opts.add_argument("--disable-background-timer-throttling")
        opts.add_argument("--disable-renderer-backgrounding")
        opts.add_argument("--disable-breakpad")
        opts.add_argument("--disable-component-update")
        opts.add_argument("--disable-domain-reliability")
        opts.add_argument("--disable-sync")
        opts.add_argument("--metrics-recording-only")
        opts.add_argument("--no-first-run")
        opts.add_argument("--mute-audio")
        opts.add_argument("--disk-cache-size=1")
        opts.add_argument("--window-size=1280,720")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--headless=new") # Usar novo modo headless estável do Chromium moderno

        # Preferências de download e segurança
        opts.add_experimental_option("prefs", {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "safebrowsing.disable_download_protection": True,
            "plugins.always_open_pdf_externally": True,
            # PERMITIR MÚLTIPLOS DOWNLOADS AUTOMATICAMENTE
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.content_settings.exceptions.automatic_downloads.*.setting": 1
        })

        self.driver = webdriver.Chrome(options=opts)
        self.driver.implicitly_wait(15)
        # self.driver.maximize_window() # Não faz sentido em modo headless
        self._log("Browser Chrome inicializado (modo headless).")

    def _ensure_driver(self):
        """Garante que o driver está vivo; recria se necessário."""
        if self.driver is None:
            self._create_driver()
            return
        try:
            _ = self.driver.current_url
        except Exception:
            self._log("Browser desconectado. Reinicializando...")
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            self.is_logged_in = False
            self.is_list_view = False
            self._create_driver()

    # -----------------------------------------------------------------------
    # LOGIN
    # -----------------------------------------------------------------------
    def _do_login(self):
        """
        Navega ao portal e realiza login se necessário.
        Flusso do TP-Link Omada:
        1. Acessar a URL do portal
        2. Se redirecionado para login, preencher email + senha
        3. Clicar em Sign In
        4. Aguardar redirecionamento para a página principal
        """

        driver = self.driver
        self._log("Acessando portal Omada Cloud...")
        self._set_status("Conectando ao portal...")

        driver.get(DEFAULT_URL)
        self._wait(5)

        # Verificar se está na página de login
        url = driver.current_url
        is_login_page = "login" in url.lower() or "id.tplink" in url.lower()

        if not is_login_page:
            self._log("Já logado ou sessão ativa.")
            self._set_status("Sessão ativa.")
            self.is_logged_in = True
            return True

        self._log("Página de login detectada.")
        self._set_status("Fazendo login...")

        try:
            wait = WebDriverWait(driver, 30)

            # --- Passo 1: Preencher email ---
            self._log("Inserindo e-mail...")
            email_field = wait.until(
                EC.presence_of_element_located((By.ID, "form_item_email"))
            )
            wait.until(EC.element_to_be_clickable((By.ID, "form_item_email")))
            email_field.click()
            email_field.clear()
            time.sleep(0.5)
            email_field.send_keys(self.email)
            self._log(f"  Email preenchido: {self.email}")

            # Aguardar a página processar o email antes de inserir a senha
            self._wait(2)

            # --- Passo 2: Preencher senha ---
            self._log("Inserindo senha...")
            password_field = wait.until(
                EC.presence_of_element_located((By.ID, "form_item_password"))
            )
            wait.until(EC.element_to_be_clickable((By.ID, "form_item_password")))
            password_field.click()
            password_field.clear()
            time.sleep(0.5)
            password_field.send_keys(self.password)
            self._log("  Senha preenchida.")

            # Aguardar um momento
            self._wait(1)

            # --- Passo 3: Clicar em Sign In ---
            self._log("Clicando em 'Sign In'...")
            login_clicked = False

            # Tentar pressionar Enter no campo de senha
            try:
                password_field.send_keys(Keys.RETURN)
                login_clicked = True
                self._log("  Enter pressionado no campo de senha.")
            except Exception:
                self._log("  Falha ao pressionar Enter. Tentando clicar no botão.")

            # Se não clicou, tentar encontrar e clicar no botão 'Sign In'
            if not login_clicked:
                try:
                    login_button = wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Sign In')] | //a[contains(., 'Sign In')] | //div[contains(., 'Sign In')] | //span[contains(., 'Sign In')] | //*[normalize-space()='Sign In']"))
                    )
                    driver.execute_script("arguments[0].click();", login_button)
                    login_clicked = True
                    self._log("  Botão 'Sign In' clicado via JS.")
                except Exception as e:
                    self._log(f"  Falha ao encontrar e clicar no botão 'Sign In': {e}")

            if not login_clicked:
                self._log("  AVISO: Nenhum botão de login foi clicado.")

            # Aguardar redirecionamento (pode demorar até 10s)
            for i in range(30):
                if not self.running:
                    return False
                url = driver.current_url
                if "login" not in url.lower() and "id.tplink" not in url.lower():
                    self._log(f"Login concluído. URL: {url}")
                    self._set_status("Login realizado.")
                    self.is_logged_in = True
                    
                    # --- NOVO: Lidar com o pop-up de aviso regional ("Aviso de Isolamento Regional") ---
                    self._handle_regional_warning()
                    
                    return True
                self._wait(1)

            self._log("AVISO: Timeout no login. Sessão pode estar ativa.")
            self._set_status("Possível problema no login.")
            self.is_logged_in = False
            return False

        except Exception as e:
            self._log(f"ERRO no login: {e}")
            self._log(f"URL: {driver.current_url}")
            try:
                path = os.path.join(
                    self.download_dir,
                    f"login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                driver.save_screenshot(path)
                self._log(f"Screenshot salvo: {path}")
            except Exception:
                pass
            return False

    # -----------------------------------------------------------------------
    # MUDAR PARA VISUALIZAÇÃO LIST
    # -----------------------------------------------------------------------
    def _handle_regional_warning(self):
        """Detecta e fecha o pop-up de aviso regional que aparece após o login (aguarda até 10s)."""
        driver = self.driver
        self._log("Aguardando aviso regional (até 10s)...")
        
        try:
            found_ok = False
            timeout = time.time() + 10
            
            while time.time() < timeout and self.running:
                # Procurar pelo botão OK do aviso
                ok_selectors = [
                    "//div[contains(@class, 'ant-modal')]//button[normalize-space()='OK']",
                    "//button[normalize-space()='OK']",
                    "//span[normalize-space()='OK']/parent::button",
                    "//div[contains(@class, 'modal')]//button[contains(., 'OK')]"
                ]
                
                # Verificar se algum botão OK está visível
                for sel in ok_selectors:
                    btns = driver.find_elements(By.XPATH, sel)
                    for btn in btns:
                        if btn.is_displayed():
                            # Encontrou o aviso! Tentar marcar "Não me volte a mostrar" primeiro
                            try:
                                checkbox = driver.find_elements(By.XPATH, "//span[contains(., 'Não me volte a mostrar')]|//input[@type='checkbox']")
                                for cb in checkbox:
                                    if cb.is_displayed():
                                        driver.execute_script("arguments[0].click();", cb)
                                        self._log("  Opção 'Não me volte a mostrar' marcada.")
                                        break
                            except:
                                pass
                            
                            # Clicar no OK
                            driver.execute_script("arguments[0].click();", btn)
                            self._log("  Aviso regional detectado e fechado.")
                            found_ok = True
                            break
                    if found_ok: break
                
                if found_ok:
                    time.sleep(2) # Aguardar animação de fechamento
                    break
                
                time.sleep(1) # Esperar 1s antes da próxima verificação
            
            if not found_ok:
                self._log("  Aviso regional não apareceu nos 10s. Prosseguindo...")
            
        except Exception as e:
            self._log(f"  Erro ao processar aviso regional: {e}")

    def _switch_to_list_view(self):
    
        driver = self.driver

        if self.is_list_view:
            return True

        self._log("Mudando para visualização LIST...")
        self._set_status("Mudando visualização...")

        try:

            WebDriverWait(driver,20).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME,"radio-button-container")
                )
            )

            radios = driver.find_elements(
                By.CLASS_NAME,
                "ant-radio-button-wrapper"
            )

            if len(radios) < 2:
                self._log("Botão LIST não encontrado.")
                return False

            # CLICA UMA ÚNICA VEZ VIA JS PARA EVITAR INTERCEPTAÇÃO POR BANNERS/HEADER
            driver.execute_script("arguments[0].click();", radios[1])

            self._log("LIST clicado.")
            self._log("Aguardando aparecer o texto Exportar...")

            timeout = time.time() + 40

            while self.running and time.time() < timeout:

                try:

                    elementos = driver.find_elements(
                        By.XPATH,
                        "//*[contains(normalize-space(.),'Exportar')]"
                    )

                    for el in elementos:

                        if el.is_displayed():

                            self._log("Texto Exportar encontrado.")
                            self.is_list_view = True
                            return True

                except Exception:
                    pass

                time.sleep(1)

            self._log("Timeout aguardando Exportar.")
            return False

        except Exception as e:

            self._log(f"Erro ao mudar para LIST: {e}")
            return False

    # -----------------------------------------------------------------------
    # EXPORTAÇÃO
    # -----------------------------------------------------------------------
    def _export_once(self):
        """
        Executa uma única exportação completa:
        1. Clicar no botão Exportar da toolbar (na tela de lista)
        2. Aguardar o pop-up de confirmação aparecer
        3. Clicar no botão Exportar do pop-up
        4. Aguardar o download e renomear
        """

        driver = self.driver
        self._log("--- Iniciando exportação ---")
        self._set_status("Exportando...")

        try:
            # --- PASSO 1: Garantir que estamos na visualização LIST ---
            if not self.is_list_view:
                # Verificar se ainda estamos logados
                if not self.is_logged_in or "login" in driver.current_url.lower():
                    self._log("Sessão expirada. Refazendo login...")
                    if not self._do_login():
                        return False
                    self._wait(3)

                if not self._switch_to_list_view():
                    return False

            # --- PASSO 2: Clicar no primeiro "Exportar" (toolbar na tela de lista) ---
            self._log("Clicando no botão Exportar da lista...")

            # Localizar o botão Exportar que está visível na tela de lista
            wait = WebDriverWait(driver, 20)
            
            # Tentar encontrar o botão Exportar na toolbar
            try:
                # Estratégia: Procurar por botões que contenham o texto 'Exportar'
                export_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Exportar')] | //a[contains(., 'Exportar')] | //span[contains(., 'Exportar')]/parent::button")
                
                export_btn = None
                for btn in export_btns:
                    if btn.is_displayed() and btn.is_enabled():
                        # Verificar se não é um botão dentro de um modal (pop-up) que ainda não apareceu
                        export_btn = btn
                        break
                
                if export_btn:
                    driver.execute_script("arguments[0].click();", export_btn)
                    self._log("  Botão Exportar da lista clicado.")
                else:
                    self._log("  AVISO: Botão Exportar da lista não encontrado via XPATH. Tentando seletor genérico.")
                    # Tentativa desesperada: qualquer elemento visível com texto Exportar
                    elements = driver.find_elements(By.XPATH, "//*[normalize-space()='Exportar']")
                    for el in elements:
                        if el.is_displayed():
                            driver.execute_script("arguments[0].click();", el)
                            self._log("  Elemento 'Exportar' clicado via JS.")
                            break
            except Exception as e:
                self._log(f"  Erro ao clicar no primeiro Exportar: {e}")
                return False

            self._wait(2)

            # --- PASSO 3: Aguardar o pop-up "Dados de exportação" e configurar as opções ---
            self._log("Aguardando pop-up 'Dados de exportação'...")

            # 1. Selecionar "Todas as Colunas"
            all_columns_selected = False
            popup_timeout = time.time() + 20
            while time.time() < popup_timeout and self.running:
                try:
                    # Procurar pelo texto "Todas as Colunas" (pode ser um radio button ou label)
                    # No Omada, costuma ser um span ou label próximo a um input do tipo radio
                    selectors = [
                        "//*[normalize-space()='Todas as Colunas']",
                        "//span[contains(., 'Todas as Colunas')]",
                        "//label[contains(., 'Todas as Colunas')]",
                        "//input[@type='radio' and following-sibling::*[contains(., 'Todas as Colunas')]]"
                    ]
                    
                    for sel in selectors:
                        els = driver.find_elements(By.XPATH, sel)
                        for el in els:
                            if el.is_displayed():
                                driver.execute_script("arguments[0].click();", el)
                                self._log("  Opção 'Todas as Colunas' selecionada.")
                                all_columns_selected = True
                                break
                        if all_columns_selected: break
                    if all_columns_selected: break
                except:
                    pass
                time.sleep(1)

            if not all_columns_selected:
                self._log("  AVISO: Não foi possível selecionar 'Todas as Colunas'. Prosseguindo com padrão.")

            self._wait(1)

            # 2. Clicar no botão verde "Exportar"
            self._log("Procurando botão final 'Exportar'...")
            export_final_clicked = False
            timeout = time.time() + 25
            
            while time.time() < timeout and self.running:
                try:
                    # Tentar encontrar todos os botões e links
                    all_buttons = driver.find_elements(By.TAG_NAME, "button")
                    all_links = driver.find_elements(By.TAG_NAME, "a")
                    all_elements = all_buttons + all_links
                    
                    candidates = []
                    for el in all_elements:
                        try:
                            text = el.text or el.get_attribute("innerText") or ""
                            if "Exportar" in text and el.is_displayed():
                                rect = el.rect
                                candidates.append({'element': el, 'y': rect['y'], 'text': text})
                        except:
                            continue
                    
                    if candidates:
                        # Priorizar o botão que está mais abaixo (o do pop-up)
                        candidates.sort(key=lambda c: c['y'], reverse=True)
                        target = candidates[0]['element']
                        
                        driver.execute_script("arguments[0].scrollIntoView(true);", target)
                        driver.execute_script("arguments[0].click();", target)
                        
                        self._log(f"  Botão '{candidates[0]['text']}' clicado.")
                        export_final_clicked = True
                        break
                except Exception as e:
                    self._log(f"  Erro ao clicar no botão final: {e}")
                
                time.sleep(1.5)

            if export_final_clicked:
                self._log("  Aguardando início do download...")
                return self._wait_for_download()
            else:
                self._log("  ERRO CRÍTICO: Não foi possível localizar o botão 'Exportar' no pop-up.")
                # Tentar um clique cego via coordenadas se nada funcionar (último recurso)
                try:
                    self._log("  Tentando clique de emergência via coordenadas...")
                    from selenium.webdriver.common.action_chains import ActionChains
                    # O botão verde costuma estar na parte inferior esquerda do modal
                    # Vamos tentar clicar em uma área provável
                    actions = ActionChains(driver)
                    actions.move_by_offset(driver.get_window_size()['width'] // 2 - 100, driver.get_window_size()['height'] // 2 + 100).click().perform()
                except:
                    pass
                
                return False

        except Exception as e:
            self._log(f"ERRO na exportação: {e}")
            try:
                path = os.path.join(
                    self.download_dir,
                    f"debug_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                )
                driver.save_screenshot(path)
                self._log(f"Screenshot salvo: {path}")
            except Exception:
                pass
            return False

    def _wait_for_download(self, timeout=45):
        """Aguarda o arquivo ser baixado, sobrescreve omada_dados.xlsx e limpa arquivos antigos."""
        start = time.time()
        target = os.path.join(self.download_dir, self.filename)

        self._log("Aguardando download do Excel...")

        while time.time() - start < timeout:
            if not self.running:
                return False

            # Procurar arquivos baixados (que não sejam omada_dados.xlsx nem crdownload)
            xlsx_files = [
                f for f in glob.glob(os.path.join(self.download_dir, "*.xlsx"))
                if os.path.abspath(f) != os.path.abspath(target) and not f.endswith(".crdownload")
            ]

            if xlsx_files:
                # Pegar o arquivo mais recente baixado
                xlsx_files.sort(key=os.path.getmtime, reverse=True)
                newest_file = xlsx_files[0]

                # Esperar 2s para garantir escrita finalizada
                self._wait(2)

                self._log(f"Download detectado: {os.path.basename(newest_file)}")
                self._rename_to_target(newest_file, target)

                # Limpar quaisquer outros arquivos antigos OrganizationList*.xlsx que tenham sobrado
                for old_f in xlsx_files[1:]:
                    try:
                        os.remove(old_f)
                    except Exception:
                        pass

                return True

            time.sleep(1)

        self._log(f"Timeout: download não concluído em {timeout}s.")
        return False

    def _rename_to_target(self, source, target):
        """Remove o destino antigo e renomeia/copia o novo arquivo para manter a base de dados única."""
        try:
            if os.path.exists(target):
                try:
                    os.remove(target)
                except Exception:
                    pass

            import shutil
            try:
                shutil.move(source, target)
            except Exception:
                shutil.copy2(source, target)
                os.remove(source)

            self._log(f"  BASE DE DADOS ATUALIZADA E SOBRESCRITA: {os.path.basename(target)}")
        except Exception as e:
            self._log(f"ERRO CRÍTICO ao atualizar base de dados: {e}")

    # -----------------------------------------------------------------------
    # LOOP PRINCIPAL
    # -----------------------------------------------------------------------
    def run(self):
        """Loop principal de exportação periódica."""
        self.running = True
        self._set_status("Rodando")
        self._log("=" * 50)
        self._log("EXPORTADOR INICIADO")
        self._log(f"  Intervalo: {self.interval}s")
        self._log(f"  Destino:   {self.download_dir}")
        self._log(f"  Arquivo:   {self.filename}")
        self._log("=" * 50)

        try:
            # Carregar dados antes de iniciar
            self.processed_data = self._load_processed_data()
            self.inep_list = self._load_ineps_from_eace()
            
            # Inicializar browser e fazer login
            self._ensure_driver()
            if not self._do_login():
                self._log("Login falhou. Tentando novamente em 10s...")
                self._wait(10)
                if not self._do_login():
                    self._log("ERRO: Login falhou 2 vezes. Abortando.")
                    self._set_status("Erro no login")
                    return

            self._wait(3)

            # Mudar para visualização LIST
            self._switch_to_list_view()
            self._wait(2)

            # Primeira exportação
            self._log("--- Exportação inicial ---")
            if self._export_once():
                self.export_count += 1
                self.last_export_time = datetime.now()
                self._log(f"Exportação #{self.export_count} concluída com sucesso.")
            else:
                self._log("Primeira exportação falhou. Tentando próxima...")

            # Fechar Chrome imediatamente após exportação inicial para liberar RAM na VPS
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
                self.is_logged_in = False
                self.is_list_view = False

            # Loop periódico
            while self.running:
                self._log(f"Aguardando {self.interval}s para próxima exportação...")
                self._wait(self.interval)

                if not self.running:
                    break

                self._log("--- Nova exportação ---")
                self._set_status("Exportando...")

                # Recriar driver do zero (garante RAM 100% limpa sem vazamento de memória)
                self._ensure_driver()
                if not self._do_login():
                    self._log("Login falhou. Tentando na próxima iteração.")
                    if self.driver:
                        try:
                            self.driver.quit()
                        except Exception:
                            pass
                        self.driver = None
                        self.is_logged_in = False
                        self.is_list_view = False
                    continue

                self._wait(3)
                self._switch_to_list_view()
                self._wait(2)

                if self._export_once():
                    self.export_count += 1
                    self.last_export_time = datetime.now()
                    self._log(f"Exportação #{self.export_count} concluída com sucesso.")
                else:
                    self._log("Falha nesta exportação. Tentando na próxima...")

                # Fechar Chrome após exportar para liberar 100% da RAM durante repouso
                if self.driver:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None
                    self.is_logged_in = False
                    self.is_list_view = False

        except Exception as e:
            self._log(f"ERRO CRÍTICO: {e}")
        finally:
            self._cleanup()

    def stop(self):
        """Solicita parada do exportador."""
        self.running = False
        self._set_status("Parando...")
        self._log("Solicitação de parada recebida.")

    def _cleanup(self):
        """Fecha o browser e limpa recursos."""
        if self.driver:
            try:
                self.driver.quit()
                self._log("Browser fechado.")
            except Exception:
                pass
            self.driver = None
        self._set_status("Parado")
        self._log("Exportador encerrado.")


# ============================================================================
# INTERFACE GRÁFICA (Tkinter)
# ============================================================================
class ExporterApp:
    """Aplicação Tkinter para controlar o exportador."""

    # Cores
    BG = "#1a1a2e"
    FG = "#e0e0e0"
    ACCENT = "#00bbd4"
    BG2 = "#16213e"
    GREEN = "#00ff88"
    RED = "#e94560"

    def __init__(self):
        self.exporter = None
        self.thread = None

        # Garantir diretório padrão
        os.makedirs(get_default_download_dir(), exist_ok=True)

        # Janela principal
        self.root = tk.Tk()
        self.root.title("Omada Cloud Data Exporter v2.0")
        self.root.geometry("720x620")
        self.root.minsize(600, 500)
        self.root.configure(bg=self.BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._update_loop()

    # -------------------------------------------------------------------
    # CONSTRUÇÃO DA UI
    # -------------------------------------------------------------------
    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=self.BG)
        style.configure("TLabel", background=self.BG, foreground=self.FG,
                        font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground=self.BG2,
                        foreground=self.FG, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=self.BG,
                        foreground=self.ACCENT, font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background=self.BG,
                        foreground=self.ACCENT, font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", background=self.BG,
                        foreground=self.ACCENT, font=("Segoe UI", 18, "bold"))
        style.configure("Status.TLabel", background=self.BG,
                        foreground=self.ACCENT, font=("Segoe UI", 12, "bold"))
        style.configure("Accent.TButton", foreground=self.GREEN,
                        font=("Segoe UI", 11, "bold"))
        style.configure("Danger.TButton", foreground=self.RED,
                        font=("Segoe UI", 11, "bold"))

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # --- Título ---
        ttk.Label(main, text="TP-Link Omada Cloud — Exportador de Dados v2.0",
                  style="Header.TLabel").pack(pady=(0, 15))

        # --- Configurações ---
        cfg = ttk.LabelFrame(main, text=" Configurações de Conexão ", padding=12)
        cfg.pack(fill=tk.X, pady=(0, 10))

        # --- NOVO: Planilha EACE ---
        eace_frame = ttk.LabelFrame(main, text=" Planilha EACE (Opcional para filtro de INEP) ", padding=12)
        eace_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.var_eace = tk.StringVar(value="")
        dir_eace = ttk.Frame(eace_frame)
        dir_eace.pack(fill=tk.X)
        ttk.Entry(dir_eace, textvariable=self.var_eace, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(dir_eace, text="📂", command=self._browse_eace).pack(side=tk.LEFT)

        r = 0
        ttk.Label(cfg, text="E-mail:").grid(row=r, column=0, sticky=tk.W, pady=4, padx=8)
        self.var_email = tk.StringVar(value=DEFAULT_EMAIL)
        ttk.Entry(cfg, textvariable=self.var_email, width=50).grid(
            row=r, column=1, sticky=tk.EW, pady=4, padx=8)

        r += 1
        ttk.Label(cfg, text="Senha:").grid(row=r, column=0, sticky=tk.W, pady=4, padx=8)
        self.var_pwd = tk.StringVar(value=DEFAULT_PASSWORD)
        pwd_entry = ttk.Entry(cfg, textvariable=self.var_pwd, width=50, show="●")
        pwd_entry.grid(row=r, column=1, sticky=tk.EW, pady=4, padx=8)

        r += 1
        ttk.Label(cfg, text="Intervalo (s):").grid(row=r, column=0, sticky=tk.W, pady=4, padx=8)
        self.var_interval = tk.StringVar(value=str(DEFAULT_INTERVAL))
        interval_frame = ttk.Frame(cfg)
        interval_frame.grid(row=r, column=1, sticky=tk.EW, pady=4, padx=8)
        ttk.Entry(interval_frame, textvariable=self.var_interval, width=10).pack(
            side=tk.LEFT, padx=(0, 8))
        ttk.Label(interval_frame, text="(mín. 10s — padrão: 30s)",
                  foreground="#888").pack(side=tk.LEFT)

        r += 1
        ttk.Label(cfg, text="Diretório:").grid(row=r, column=0, sticky=tk.W, pady=4, padx=8)
        dir_frame = ttk.Frame(cfg)
        dir_frame.grid(row=r, column=1, columnspan=2, sticky=tk.EW, pady=4, padx=8)
        self.var_dir = tk.StringVar(value=get_default_download_dir())
        ttk.Entry(dir_frame, textvariable=self.var_dir, width=40).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(dir_frame, text="📂", command=self._browse_dir).pack(side=tk.LEFT)

        r += 1
        ttk.Label(cfg, text="Arquivo:").grid(row=r, column=0, sticky=tk.W, pady=4, padx=8)
        self.var_file = tk.StringVar(value=DEFAULT_FILENAME)
        ttk.Entry(cfg, textvariable=self.var_file, width=50).grid(
            row=r, column=1, sticky=tk.EW, pady=4, padx=8)

        cfg.columnconfigure(1, weight=1)

        # --- Botões de Controle ---
        ctrl = ttk.Frame(main)
        ctrl.pack(fill=tk.X, pady=12)

        self.btn_start = ttk.Button(
            ctrl, text="▶  INICIAR EXPORTAÇÃO", style="Accent.TButton",
            command=self._start)
        self.btn_start.pack(side=tk.LEFT, padx=10, ipadx=15, ipady=8)

        self.btn_stop = ttk.Button(
            ctrl, text="■  PARAR", style="Danger.TButton",
            command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10, ipadx=15, ipady=8)

        # --- Status ---
        self.lbl_status = ttk.Label(main, text="Status: Parado",
                                    style="Status.TLabel")
        self.lbl_status.pack(pady=8)

        self.lbl_stats = ttk.Label(
            main, text="Exportações: 0  |  Última: --  |  Próxima: --",
            font=("Segoe UI", 10), foreground=self.FG)
        self.lbl_stats.pack(pady=2)

        # --- Log ---
        log_frame = ttk.LabelFrame(main, text=" Log de Atividade ", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.txt_log = tk.Text(
            log_frame, height=10, bg=self.BG2, fg=self.GREEN,
            font=("Consolas", 9), state=tk.DISABLED, wrap=tk.WORD,
            relief=tk.FLAT, borderwidth=0, insertbackground=self.GREEN)
        sb = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        self.txt_log.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # -------------------------------------------------------------------
    # EVENTOS DA UI
    # -------------------------------------------------------------------
    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.var_dir.get())
        if d:
            self.var_dir.set(d)

    def _browse_eace(self):
        f = filedialog.askopenfilename(
            title="Selecionar Planilha EACE",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if f:
            self.var_eace.set(f)

    def _log(self, msg):
        """Envia mensagem de log para a thread principal."""
        self.root.after(0, lambda m=msg: self._append_log(m))

    def _append_log(self, msg):
        self.txt_log.configure(state=tk.NORMAL)
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.configure(state=tk.DISABLED)

    def _on_status(self, text):
        self.root.after(0, lambda t=text: self.lbl_status.configure(text=f"Status: {t}"))

    def _update_loop(self):
        """Atualiza estatísticas a cada 1 segundo."""
        if self.exporter:
            last = "--"
            if self.exporter.last_export_time:
                last = self.exporter.last_export_time.strftime("%H:%M:%S")
            next_t = f"em {self.exporter.interval}s" if self.exporter.running else "--"
            self.lbl_stats.configure(
                text=f"Exportações: {self.exporter.export_count}  |  "
                     f"Última: {last}  |  Próxima: {next_t}")
        self.root.after(1000, self._update_loop)

    # -------------------------------------------------------------------
    # CONTROLE DO EXPORTADOR
    # -------------------------------------------------------------------
    def _start(self):
        """Inicia o exportador em thread separada."""
        try:
            interval = int(self.var_interval.get())
            if interval < 10:
                messagebox.showwarning("Atenção", "O intervalo mínimo é 10 segundos.")
                return
        except ValueError:
            messagebox.showerror("Erro", "Intervalo deve ser um número inteiro.")
            return

        # Criar diretório
        ddir = self.var_dir.get()
        os.makedirs(ddir, exist_ok=True)

        # Instanciar exportador
        self.exporter = OmadaExporter(
            email=self.var_email.get(),
            password=self.var_pwd.get(),
            interval=interval,
            download_dir=ddir,
            filename=self.var_file.get(),
            eace_path=self.var_eace.get()
        )
        self.exporter.on_log = self._log
        self.exporter.on_status = self._on_status

        # Atualizar UI
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self._set_fields_state(tk.DISABLED)
        self._log("Iniciando exportador...")

        # Thread
        self.thread = threading.Thread(target=self.exporter.run, daemon=True)
        self.thread.start()

    def _stop(self):
        """Para o exportador."""
        if self.exporter:
            self.exporter.stop()
        self._log("Parando exportador... Aguarde...")

    def _set_fields_state(self, state):
        """Ativa/desativa campos de configuração."""
        for child in self.root.winfo_children():
            self._disable_recursive(child, state)

    def _disable_recursive(self, widget, state):
        skip = (self.btn_start, self.btn_stop)
        for ch in widget.winfo_children():
            if ch in skip:
                continue
            if isinstance(ch, (ttk.Entry,)):
                ch.configure(state=state)
            elif hasattr(ch, 'winfo_children'):
                self._disable_recursive(ch, state)

    def _on_close(self):
        """Fecha a aplicação."""
        if self.exporter and self.exporter.running:
            if messagebox.askyesno("Confirmar",
                                   "O exportador está rodando.\nDeseja realmente fechar?"):
                self.exporter.stop()
                self.root.after(2000, self.root.destroy)
            return
        self.root.destroy()


# ============================================================================
# MAIN
# ============================================================================
def run_cli_mode(args):
    """Executa o exportador em modo CLI (sem interface gráfica Tkinter)."""
    email = args.email or os.getenv("OMADA_EMAIL", DEFAULT_EMAIL)
    password = args.password or os.getenv("OMADA_PASSWORD", DEFAULT_PASSWORD)
    interval = args.interval or int(os.getenv("OMADA_INTERVAL", DEFAULT_INTERVAL))
    download_dir = args.dir or os.getenv("OMADA_DIR", get_default_download_dir())

    print("=" * 60)
    print("  Omada Cloud Data Exporter v2.0 (MODO CLI / DOCKER)")
    print("=" * 60)
    print(f"E-mail:    {email}")
    print(f"Intervalo: {interval}s")
    print(f"Diretório: {download_dir}")
    print("=" * 60)

    exporter = OmadaExporter(
        email=email,
        password=password,
        interval=interval,
        download_dir=download_dir,
        filename=DEFAULT_FILENAME
    )

    def cli_log(msg):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

    exporter.on_log = cli_log
    try:
        exporter.run()
    except (KeyboardInterrupt, SystemExit):
        print("\nInterrupção recebida. Parando exportador CLI...")
        exporter.stop()
        print("Exportador CLI encerrado.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Omada Cloud Data Exporter")
    parser.add_argument("--cli", action="store_true", help="Rodar em modo terminal (sem janela gráfica)")
    parser.add_argument("--email", type=str, help="E-mail de login")
    parser.add_argument("--password", type=str, help="Senha de login")
    parser.add_argument("--interval", type=int, help="Intervalo em segundos entre exportações")
    parser.add_argument("--dir", type=str, help="Diretório de saída para os relatórios XLSX")
    args, _ = parser.parse_known_args()

    # Se --cli for passado OU a variável de ambiente OMADA_CLI=true estiver setada OU tkinter não estiver disponível
    if args.cli or str(os.getenv("OMADA_CLI", "")).lower() in ("true", "1", "yes") or not TKINTER_AVAILABLE:
        run_cli_mode(args)
        return

    print("=" * 60)
    print("  Omada Cloud Data Exporter v2.0 (MODO GUI)")
    print("  Python:", sys.version.split()[0])
    print("=" * 60)
    print()

    # Verificar dependências
    try:
        import selenium  # noqa: F401
    except ImportError:
        print("ERRO: Selenium não instalado.")
        print("Execute: pip install selenium")
        input("Pressione Enter para sair...")
        sys.exit(1)

    app = ExporterApp()
    app.root.mainloop()


if __name__ == "__main__":
    main()

