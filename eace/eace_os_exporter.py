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
from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ============================================================================
# CONFIGURAÇÕES E CAMINHOS
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados_eace")
TEMP_DOWNLOAD_DIR = os.path.join(BASE_DIR, "temp_downloads")

LOGIN_URL = "https://eace.org.br/login"
EMAIL_DEFAULT = os.getenv("EACE_EMAIL", "noc@bitinternet.com.br")
PASSWORD_DEFAULT = os.getenv("EACE_PASSWORD", "")

FILE_RI = os.path.join(DADOS_DIR, "controle_os_ri.xlsx")


class EACEOSExporter:
    def __init__(self, email=EMAIL_DEFAULT, password=PASSWORD_DEFAULT, headless=True, intervalo=0):
        self.email = email
        self.password = password
        self.headless = headless
        self.intervalo = intervalo
        self.driver = None
        self._setup_dirs()

    def _setup_dirs(self):
        for path in [DADOS_DIR, TEMP_DOWNLOAD_DIR]:
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
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--disable-extensions")
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
        opts.add_argument("--window-size=1920,1080")

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
            time.sleep(5)

            # Preencher credenciais
            for inp in self.driver.find_elements(By.TAG_NAME, "input"):
                t = inp.get_attribute("type")
                placeholder = (inp.get_attribute("placeholder") or "").lower()
                if t == "email" or "email" in placeholder:
                    inp.clear()
                    inp.send_keys(self.email)
                elif t == "password":
                    inp.clear()
                    inp.send_keys(self.password)
                    inp.send_keys(Keys.RETURN)
                    break

            time.sleep(10)
            self.log(f"URL após Log In: {self.driver.current_url}")

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
            # Mapear os botões de ícone da barra superior direita
            buttons = []
            for btn in self.driver.find_elements(By.TAG_NAME, "button"):
                r = btn.rect
                if r["x"] > 1500 and 100 < r["y"] < 250 and r["width"] < 60:
                    buttons.append((r["x"], btn))
            buttons.sort(key=lambda item: item[0])

            if not buttons:
                self.log("Erro: Botão de download do RI não encontrado na barra superior direita.")
                return False

            # O primeiro botão na barra corresponde ao RI
            x_pos, btn_element = buttons[0]
            self.log(f"Clicando no botão de download RI na posição X={x_pos} via JS...")
            self.driver.execute_script("arguments[0].click();", btn_element)

            # Aguardar o novo arquivo na pasta temporária
            timeout = 45
            inicio = time.time()
            arquivo_baixado = None

            while time.time() - inicio < timeout:
                files = glob.glob(os.path.join(TEMP_DOWNLOAD_DIR, "*.xlsx"))
                if files and not any(f.endswith(".crdownload") for f in glob.glob(os.path.join(TEMP_DOWNLOAD_DIR, "*"))):
                    files_sorted = sorted(files, key=os.path.getmtime, reverse=True)
                    arquivo_baixado = files_sorted[0]
                    break
                time.sleep(2)

            if not arquivo_baixado:
                self.log("Timeout ao aguardar download da planilha RI.")
                return False

            # Sobrescrever arquivo destino em dados_eace/controle_os_ri.xlsx
            if os.path.exists(FILE_RI):
                os.remove(FILE_RI)
            shutil.move(arquivo_baixado, FILE_RI)
            self.log(f"SUCESSO: Planilha RI atualizada -> {FILE_RI}")
            return True

        except Exception as e:
            self.log(f"Erro ao baixar planilha RI: {e}")
            return False

    def run(self):
        self._limpar_temp()
        self.init_driver()
        try:
            sucesso_nav = self.login_e_navegar()
            if not sucesso_nav:
                self.log("FALHA: Não foi possível chegar à página de chamados.")
                return False

            self.log("==== Baixando Planilha RI (Rede Interna) ====")
            return self.export_ri()

        finally:
            if self.driver:
                self.driver.quit()
            self._limpar_temp()


def main():
    parser = argparse.ArgumentParser(description="EACE OS Exporter - Automação de Chamados RI (Rede Interna)")
    parser.add_argument("--no-headless", action="store_true", help="Executar com navegador visível (GUI)")
    parser.add_argument("--intervalo", type=int, default=0, help="Intervalo em segundos para repetição em loop (0 = execução única)")
    args = parser.parse_args()

    headless = not args.no_headless
    intervalo = args.intervalo

    exporter = EACEOSExporter(headless=headless, intervalo=intervalo)

    if intervalo > 0:
        print(f"[EACE Exporter] Modo contínuo ativado (intervalo: {intervalo}s).")
        print("[EACE Exporter] Aguardando 180s (3 min) de delay inicial para que o Omada Exporter conclua na VPS...")
        time.sleep(180)
        while True:
            exporter.run()
            time.sleep(intervalo)
    else:
        exporter.run()


if __name__ == "__main__":
    main()
