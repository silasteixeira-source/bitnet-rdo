# EACE OS Exporter — Robô de Exportação de OS (Rede Interna - RI)

Robô automatizado para portal Aprender Conectado (EACE), realizando login, navegação ao painel de Fornecedor, acesso ao Gerenciador de Chamados e download contínuo da planilha **RI (Rede Interna)**.

---

## 1. Como rodar localmente no Windows

### Pré-requisitos:
- Python 3.10 ou superior
- Google Chrome instalado

### Instalação e execução:
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute o robô:
   ```bash
   # Rodar uma vez em modo silencioso (invisível):
   python eace_os_exporter.py

   # Rodar com o navegador aberto na tela (para acompanhar visualmente):
   python eace_os_exporter.py --no-headless

   # Rodar em loop contínuo a cada 1 hora (3600 segundos):
   python eace_os_exporter.py --intervalo 3600
   ```
O arquivo sempre será salvo e atualizado em `dados_eace/controle_os_ri.xlsx`.

---

## 2. Como rodar na VPS Linux (Headless via Docker)

Sua VPS não possui interface gráfica. Por isso, preparamos a conteinerização com **Chromium Headless** nativo.

### Comandos na VPS:
1. Dentro da pasta `eace/`:
   ```bash
   docker compose up -d --build
   ```
2. Ver logs do robô trabalhando:
   ```bash
   docker compose logs -f
   ```
3. A planilha atualizada em tempo real ficará disponível em:
   ```bash
   dados_eace/controle_os_ri.xlsx
   ```
