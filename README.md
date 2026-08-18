# 🛠️ NOC RDO & Omada Exporter - Multi-Tenant

Este repositório contém a automação de cruzamento de dados do NOC, integrando o **Omada Cloud Controller** e os **Relatórios de OS (Bubble/EACE)** para os projetos **BITNET** e **ST1**.

## 🚀 Como Instalar e Rodar em uma Nova Máquina (VPS)

Para evitar sobrecarga de memória RAM (o famoso erro `tab crashed` do Google Chrome em modo Headless), os robôs foram programados para rodar de forma **sequencial**. O Omada roda primeiro e, 3 minutos depois, o EACE entra em ação. 

Para que os cronômetros fiquem perfeitamente sincronizados, siga EXATAMENTE a ordem abaixo ao clonar ou atualizar o repositório:

```bash
# 1. Clone o repositório
git clone https://github.com/silasteixeira-source/bitnet-rdo.git
cd bitnet-rdo

# 2. Configure as Variáveis de Ambiente (Senhas e Credenciais)
# Crie uma cópia do arquivo de exemplo para o arquivo definitivo (.env) e edite-o
cp .env.example .env
nano .env  # Preencha os emails, senhas e configurações de intervalo do Omada e EACE

# 3. Pare qualquer container que possa estar rodando fora de sincronia
sudo docker compose down

# 4. Construa as imagens do zero
sudo docker compose build --no-cache

# 5. Inicie os containers SIMULTANEAMENTE
# (Isso garante que os timers do Omada e EACE fiquem sincronizados e não estourem a RAM)
sudo docker compose up -d

# 6. Acompanhe os logs
sudo docker compose logs -f
```

---

## 🛑 Alerta de Manutenção (OOM Killer / Tab Crashed)
Se os robôs começarem a apresentar falhas de memória (`Message: tab crashed`), significa que a VPS ficou sem RAM e os containers acabaram se sobrepondo ou o servidor está sobrecarregado.

**Solução rápida:**
1. Execute `sudo docker compose down` para desligar tudo.
2. Inicie novamente com `sudo docker compose up -d` para resetar os cronômetros de delay (o EACE sempre aguarda 3 minutos iniciais).
3. Considere [adicionar Memória SWAP no Linux](https://linuxize.com/post/how-to-add-swap-space-on-ubuntu-20-04/) se sua máquina tiver apenas 4GB de RAM e estiver rodando outros serviços como Chatwoot/Evolution.

## 🌐 Painel Streamlit (Manual)
O sistema conta com uma interface web para cruzamentos manuais ou consultas rápidas.
Para acessar, basta verificar a porta mapeada no `docker-compose.yml` (geralmente `http://IP_DA_VPS:8501`). Pelo site, você pode selecionar o projeto (BITNET ou ST1) e rodar unificações independentes.
