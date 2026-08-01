# Guia de Execução no Docker e VPS (Linux/Windows) - Omada Exporter CLI

Este diretório contém a versão conteinerizada e preparada para execução 24/7 em servidores (VPS) do **Omada Cloud Data Exporter**, rodando de forma 100% headless (sem interface gráfica) via **Chromium + Selenium**.

---

## 1. Pré-requisitos na VPS
1. **Docker** e **Docker Compose** instalados na VPS:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
   ```
2. Clonar ou atualizar seu repositório Git na VPS:
   ```bash
   git pull origin main
   cd omada
   ```

---

## 2. Configurando Senha e Variáveis de Ambiente (`.env`)
Para manter a segurança das credenciais, crie um arquivo chamado **`.env`** dentro da pasta `omada/` (esse arquivo já é ignorado pelo Git):
```bash
nano .env
```
Cole o seguinte conteúdo com a senha da equipe:
```ini
OMADA_EMAIL=noceace@bitinternet.com.br
OMADA_PASSWORD="SUA_SENHA_AQUI"
OMADA_INTERVAL=30
```

---

## 3. Subindo o Serviço via Docker Compose
Dentro da pasta `omada/`, execute:
```bash
docker compose up -d --build
```

O Docker irá:
1. Construir a imagem Python 3.11 com o **Chromium** e **ChromeDriver**.
2. Subir o serviço `omada-exporter` em segundo plano com a regra de reinício automático (`restart: unless-stopped`).
3. Montar a pasta local `./dados_omada` de forma sincronizada com o container.

---

## 4. Monitoramento na VPS
- **Acompanhar os logs em tempo real**:
  ```bash
  docker compose logs -f
  ```
- **Verificar se o arquivo XLSX foi atualizado**:
  ```bash
  ls -la dados_omada/
  ```
- **Parar ou reiniciar o serviço**:
  ```bash
  docker compose restart    # Reiniciar
  docker compose down       # Parar e remover o container
  ```
