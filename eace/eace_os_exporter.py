# -*- coding: utf-8 -*-
"""
EACE OS Exporter - Robô de Exportação Automática de OS (RI - Rede Interna)
Compatível com Windows e VPS Linux (Headless via Docker / CLI).

Fluxo Automático:
1. Login em https://eace.org.br/login
2. Seleção de perfil "Fornecedor"
3. Navegação ao menu "Gerenciar Chamados" (Fluxos OS)
4. Exportação da planilha RI (Rede Interna)
5. Sobrescrita sempre da versão mais recente em dados_eace/controle_os_ri.xlsx
"""

import os
import sys
import time
import glob
import shutil
import argparse
import subprocess
from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================================
# CONFIGURAÇÕES E CAMINHOS
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DADOS_DIR = os.path.join(BASE_DIR, "dados_eace")
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")

LOGIN_URL = "https://eace.org.br/login"
EMAIL_DEFAULT = os.getenv("EACE_EMAIL", "noc@bitinternet.com.br")
PASSWORD_DEFAULT = os.getenv("EACE_PASSWORD", "")

class EACEOSExporter:
    def __init__(self, email=EMAIL_DEFAULT, password=PASSWORD_DEFAULT, headless=True, intervalo=0, dados_dir=DEFAULT_DADOS_DIR, rdo_url=None, dest_url=None, omada_url=None, omada_old=None, omada_new=None, label="BITNET"):
        self.email = email
        self.password = password
        self.headless = headless
        self.intervalo = intervalo
        self.dados_dir = dados_dir
        self.rdo_url = rdo_url or os.getenv("RDO_SPREADSHEET_URL", "https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit?gid=1631182129#gid=1631182129")
        self.dest_url = dest_url or os.getenv("DESTINATION_GSHEET_URL", "https://docs.google.com/spreadsheets/d/167LUrFFBJBlQ-Jh7cX717r32F2c8tfq1zsx_0FIC0WY/edit")
        self.omada_url = omada_url or os.getenv("DESTINATION_OMADA_URL", "https://docs.google.com/spreadsheets/d/1r8jQ8jJGWSLQoACVoBy8emYlk3avJOuEXM10W_tlY-o/edit?gid=998874036#gid=998874036")
        self.omada_old = omada_old or "/app/omada/dados_omada/omada_dados_anterior.xlsx"
        self.omada_new = omada_new or "/app/omada/dados_omada/omada_dados.xlsx"
        self.label = label
        self.file_ri = os.path.join(self.dados_dir, "controle_os_ri.xlsx")
        self.driver = None
        self._setup_dirs()

    def _setup_dirs(self):
        for path in [self.dados_dir, TEMP_DOWNLOAD_DIR]:
            os.makedirs(path, exist_ok=True)
        self._limpar_temp()

    def _limpar_temp(self):
        for f in glob.glob(os.path.join(TEMP_DOWNLOAD_DIR, "*")):
            try:
                os.remove(f)
            except Exception:
                pass

    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] [EACE Exporter] {msg}", flush=True)

    def init_driver(self):
        self.log("Inicializando Google Chrome / Chromium...")
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu-compositing")
        opts.add_argument("--disable-smooth-scrolling")
        opts.add_argument("--js-flags=--max-old-space-size=2048")
        opts.add_argument("--disable-setuid-sandbox")
        opts.add_argument("--disable-accelerated-2d-canvas")
        opts.add_argument("--disable-accelerated-jpeg-decoding")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--remote-debugging-pipe")
        opts.add_argument("--remote-allow-origins=*")
        opts.add_argument("--disable-features=VizDisplayCompositor,NetworkService,NetworkServiceInProcess")
        opts.add_argument("--disable-ipc-flooding-protection")
        opts.add_argument("--disable-hang-monitor")
        opts.add_argument("--no-zygote")
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

        prefs = {
            "download.default_directory": TEMP_DOWNLOAD_DIR,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        opts.add_experimental_option("prefs", prefs)

        self.driver = webdriver.Chrome(options=opts)
        self.driver.implicitly_wait(10)

    def login_e_navegar(self):
        try:
            self.log(f"1. Acessando portal de Login: {LOGIN_URL}")
            self.driver.get(LOGIN_URL)
            
            # Aguardar até 25 segundos para os inputs renderizarem (Bubble.io / Cloudflare)
            for _ in range(5):
                if len(self.driver.find_elements(By.TAG_NAME, "input")) >= 2:
                    break
                time.sleep(5)

            # Preencher credenciais
            email_preenchido = False
            senha_preenchida = False
            for inp in self.driver.find_elements(By.TAG_NAME, "input"):
                t = (inp.get_attribute("type") or "").lower()
                name = (inp.get_attribute("name") or "").lower()
                id_attr = (inp.get_attribute("id") or "").lower()
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                
                if not email_preenchido and (t == "email" or any(k in name or k in id_attr or k in placeholder for k in ["email", "e-mail", "user", "usuari", "login", "cpf", "cnpj"]) or (t == "text" and not email_preenchido)):
                    try:
                        inp.clear()
                        inp.send_keys(self.email)
                        email_preenchido = True
                        self.log(f" -> Campo de usuário/e-mail preenchido: {self.email}")
                    except Exception:
                        pass
                elif t == "password" and not senha_preenchida:
                    try:
                        inp.clear()
                        inp.send_keys(self.password)
                        senha_preenchida = True
                        self.log(" -> Campo de senha preenchido.")
                        inp.send_keys(Keys.RETURN)
                    except Exception:
                        pass
                    break

            if not email_preenchido:
                self.log("❌ AVISO: Não foi detectado campo de e-mail/usuário na tela de login!")
            if not senha_preenchida:
                self.log("❌ AVISO: Não foi detectado campo de senha na tela de login!")

            time.sleep(2)
            # Garantir clique explícito no botão de Log In / Entrar / Acessar via JS
            botoes = self.driver.find_elements(By.XPATH, "//button | //input[@type='submit'] | //*[@role='button'] | //a[contains(@class, 'btn')]")
            self.log(f"Botões detectados na tela de login: {[b.text.strip() or str(b.get_attribute('value')) for b in botoes]}")
            clicado = False
            # 1. Prioridade máxima: Botões cujo texto ou value seja explicitamente de login/acesso
            for b in botoes:
                txt = (b.text or str(b.get_attribute("value") or "") or str(b.get_attribute("aria-label") or "")).strip()
                txt_lower = txt.lower()
                if not txt_lower:
                    continue
                if any(k in txt_lower for k in ["log in", "login", "entrar", "acessar", "sign in", "continuar", "próximo", "avançar"]):
                    try:
                        self.driver.execute_script("arguments[0].click();", b)
                        clicado = True
                        self.log(f" -> Botão de login clicado (por texto): '{txt}'")
                        break
                    except Exception:
                        try:
                            b.click()
                            clicado = True
                            self.log(f" -> Botão de login clicado (via click): '{txt}'")
                            break
                        except Exception:
                            pass
            # 2. Fallback: se nenhum botão com texto explícito foi clicado, tenta botão com type='submit'
            if not clicado:
                for b in botoes:
                    if b.get_attribute("type") == "submit":
                        try:
                            self.driver.execute_script("arguments[0].click();", b)
                            clicado = True
                            self.log(" -> Botão submit (fallback) clicado.")
                            break
                        except Exception:
                            pass

            time.sleep(12)
            self.log(f"URL após Log In: {self.driver.current_url}")
            if "login" in self.driver.current_url.lower():
                try:
                    corpo_txt = self.driver.find_element(By.TAG_NAME, "body").text
                    alertas = [linha for linha in corpo_txt.split("\n") if any(w in linha.lower() for w in ["erro", "inválid", "incorret", "credencial", "falha", "obrigatório", "captcha", "bloquead"])]
                    if alertas:
                        self.log(f" -> Avisos detectados na tela de login: {alertas}")
                except Exception:
                    pass

            # Passo 2: Clicar em "Fornecedor" no modal de seleção de perfil
            self.log("2. Selecionando perfil Fornecedor...")
            for el in self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Fornecedor') or contains(text(), 'FORNECEDOR')]"):
                try:
                    el.click()
                    self.log(" -> Perfil 'Fornecedor' selecionado com sucesso.")
                    break
                except Exception:
                    pass

            time.sleep(10)
            self.log(f"URL no Painel do Fornecedor: {self.driver.current_url}")

            # Passo 3: Clicar em "Gerenciar Chamados"
            self.log("3. Abrindo 'Gerenciar Chamados' (Fluxos OS)...")
            for el in self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Gerenciar') or contains(text(), 'Chamados')]"):
                try:
                    if "gerenciar" in el.text.lower() and "chamado" in el.text.lower():
                        el.click()
                        self.log(" -> 'Gerenciar Chamados' clicado com sucesso.")
                        break
                except Exception:
                    pass

            time.sleep(15)
            self.log(f"URL final na tela de OS: {self.driver.current_url}")
            return "np_fluxos_os" in self.driver.current_url

        except Exception as e:
            self.log(f"Erro durante login e navegação: {e}")
            return False

    def export_ri(self):
        """
        Clica no ícone de download da planilha RI (Rede Interna) no canto superior direito.
        """
        try:
            self.log("Buscando botão de exportação da planilha RI (Rede Interna)...")
            # Mapear os botões da barra de ferramentas superior onde ficam RI (X ≈ 1180) e RE (X ≈ 1210)
            export_btns = []
            todos_botoes = self.driver.find_elements(By.TAG_NAME, "button")
            for b in todos_botoes:
                try:
                    r = b.rect
                    # Filtra apenas ícones pequenos (width < 60) na área de exportação para ignorar "Adicionar nova OS"
                    if 1150 < r['x'] < 1250 and r['y'] < 250 and r['width'] < 60:
                        export_btns.append((r['x'], b))
                except Exception:
                    pass
            export_btns.sort(key=lambda x: x[0])
            self.log(f" -> Botões de exportação pequenos (width < 60) na faixa (1150 < X < 1250): {len(export_btns)} (X: {[int(item[0]) for item in export_btns]})")

            if not export_btns:
                coord_todos = [int(b.rect["x"]) for b in todos_botoes if b.rect["y"] < 250 and b.rect["width"] < 60]
                self.log(f"❌ Erro: Nenhum ícone de download (RI/RE) encontrado na faixa X ≈ 1180-1210. Todos os ícones em Y<250: X={coord_todos}")
                return False

            # O RI é o primeiro da esquerda nesta faixa (menor X, ≈ 1180)
            x_pos, ri_btn = export_btns[0]
            self.log(f" -> Botão RI selecionado: X={int(x_pos)} (primeiro ícone da esquerda)")
            self.log(f" -> Clicando no botão da Planilha RI via JS execute_script...")
            self.driver.execute_script("arguments[0].click();", ri_btn)

            # Aguardar o novo arquivo na pasta temporária (aumentado para 120s para servidores lentos do Bubble.io)
            timeout = 120
            inicio = time.time()
            arquivo_baixado = None

            while time.time() - inicio < timeout:
                files = [f for f in glob.glob(os.path.join(TEMP_DOWNLOAD_DIR, "*.*")) if not f.endswith(".crdownload") and not f.endswith(".tmp")]
                if files:
                    files_sorted = sorted(files, key=os.path.getmtime, reverse=True)
                    arquivo_baixado = files_sorted[0]
                    break
                time.sleep(2)

            if not arquivo_baixado:
                self.log("❌ Timeout (120s) ao aguardar download da planilha RI gerada pelo Bubble.io.")
                return False

            # Sobrescrever arquivo destino
            if os.path.exists(self.file_ri):
                os.remove(self.file_ri)
            shutil.move(arquivo_baixado, self.file_ri)
            self.log(f"SUCESSO: Planilha RI atualizada -> {self.file_ri}")

            # --- DISPARO AUTOMÁTICO DO UNIFICADOR (CRUZAMENTO EM TEMPO REAL) ---
            self.log(f"⚡ Download da EACE concluído! Disparando cruzamento das planilhas (Omada + EACE + RDO) para {self.label}...")
            try:
                cmd = [
                    sys.executable, "-u", "unificador_auto.py",
                    "--old", self.omada_old,
                    "--new", self.omada_new,
                    "--os", self.file_ri,
                    "--rdo", self.rdo_url,
                    "--url", self.dest_url,
                    "--omada-url", self.omada_url,
                    "--tenant", self.label.lower(),
                    "--intervalo", "0"
                ]
                subprocess.run(cmd, check=False)
            except Exception as e_unif:
                self.log(f"⚠️ Erro ao disparar cruzamento no unificador_auto.py: {e_unif}")

            return True

        except Exception as e:
            self.log(f"Erro ao baixar planilha RI: {e}")
            return False

    def run(self):
        max_tentativas = 3
        for tentativa in range(1, max_tentativas + 1):
            if tentativa > 1:
                self.log(f"🔄 Tentativa de retry {tentativa}/{max_tentativas} após falha transitória (aguardando 20s)...")
                time.sleep(20)
            self._limpar_temp()
            self.init_driver()
            try:
                sucesso_nav = self.login_e_navegar()
                if not sucesso_nav:
                    self.log(f"FALHA na tentativa {tentativa}: Não foi possível chegar à página de chamados.")
                    continue

                self.log("==== Baixando Planilha RI (Rede Interna) ====")
                if self.export_ri():
                    return True
                else:
                    self.log(f"FALHA na tentativa {tentativa}: Download do arquivo RI não concluído.")
            except Exception as e_run:
                self.log(f"⚠️ Erro inesperado na tentativa {tentativa}: {e_run}")
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                self._limpar_temp()
        self.log("❌ Todas as tentativas do ciclo falharam. O robô aguardará o próximo ciclo agendado.")
        return False


def main():
    parser = argparse.ArgumentParser(description="EACE OS Exporter - Automação de Chamados RI (Multi-Tenant)")
    parser.add_argument("--no-headless", action="store_true", help="Executar com navegador visível (GUI)")
    parser.add_argument("--intervalo", type=int, default=0, help="Intervalo em segundos para repetição em loop (0 = execução única)")
    args = parser.parse_args()

    headless = not args.no_headless
    intervalo = args.intervalo or int(os.getenv("INTERVALO_SEGUNDOS", 300))

    # --- Configurar Exportador BITNET ---
    exporter_bitnet = EACEOSExporter(
        email=os.getenv("EACE_EMAIL", "noc@bitinternet.com.br"),
        password=os.getenv("EACE_PASSWORD", ""),
        headless=headless,
        intervalo=intervalo,
        dados_dir=DEFAULT_DADOS_DIR,
        omada_old="/app/omada/dados_omada/omada_dados_anterior.xlsx" if os.path.exists("/app/omada/dados_omada/omada_dados_anterior.xlsx") else "omada/dados_omada/omada_dados_anterior.xlsx",
        omada_new="/app/omada/dados_omada/omada_dados.xlsx" if os.path.exists("/app/omada/dados_omada/omada_dados.xlsx") else "omada/dados_omada/omada_dados.xlsx",
        rdo_url="https://docs.google.com/spreadsheets/d/1eHZwGEo4-wQ4kvZvNU2mRFx-D3elurKk/edit?gid=1631182129#gid=1631182129",
        dest_url="https://docs.google.com/spreadsheets/d/167LUrFFBJBlQ-Jh7cX717r32F2c8tfq1zsx_0FIC0WY/edit",
        omada_url="https://docs.google.com/spreadsheets/d/1r8jQ8jJGWSLQoACVoBy8emYlk3avJOuEXM10W_tlY-o/edit?gid=998874036#gid=998874036",
        label="BITNET"
    )

    # --- Configurar Exportador ST1 ---
    email_st1 = os.getenv("EACE_ST1_EMAIL", "")
    password_st1 = os.getenv("EACE_ST1_PASSWORD", "")
    
    exporter_st1 = None
    if email_st1 and password_st1:
        exporter_st1 = EACEOSExporter(
            email=email_st1,
            password=password_st1,
            headless=headless,
            intervalo=intervalo,
            dados_dir=os.path.join(BASE_DIR, "dados_st1"),
            omada_old="/app/omada/dados_st1/omada_dados_anterior.xlsx" if os.path.exists("/app/omada/dados_st1/omada_dados_anterior.xlsx") else "omada/dados_st1/omada_dados_anterior.xlsx",
            omada_new="/app/omada/dados_st1/omada_dados.xlsx" if os.path.exists("/app/omada/dados_st1/omada_dados.xlsx") else "omada/dados_st1/omada_dados.xlsx",
            rdo_url="https://docs.google.com/spreadsheets/d/1IoTyZ4fmgUwvdLYtEC_9UqgIDBmuLH_o/edit?gid=483331132#gid=483331132",
            dest_url="https://docs.google.com/spreadsheets/d/1jMc7SW8ECb49j1LP8W879Xz-wyxudkkMYCH9s7nKVdU/edit",
            omada_url="https://docs.google.com/spreadsheets/d/1wDbFAKnbf62CvW7byBM5yXXMUAx2lwoquvOC59xJmN4/edit?gid=998874036#gid=998874036",
            label="ST1"
        )

    if args.intervalo > 0 or intervalo > 0:
        print(f"[EACE Exporter] Modo contínuo ativado (intervalo: {intervalo}s - 5 min).")
        print("[EACE Exporter] Aguardando 180s (3 min) de delay inicial para que o Omada Exporter conclua na VPS...")
        time.sleep(180)
        while True:
            print("\n[EACE Exporter] === Iniciando Processamento EACE -> BITNET ===")
            exporter_bitnet.run()
            
            if exporter_st1:
                print("\n[EACE Exporter] === Iniciando Processamento EACE -> ST1 ===")
                exporter_st1.run()
                
            print(f"\n[EACE Exporter] Aguardando {intervalo}s para o próximo ciclo global...")
            time.sleep(intervalo)
    else:
        print("\n[EACE Exporter] === Iniciando Processamento EACE -> BITNET ===")
        exporter_bitnet.run()
        if exporter_st1:
            print("\n[EACE Exporter] === Iniciando Processamento EACE -> ST1 ===")
            exporter_st1.run()


if __name__ == "__main__":
    main()
