# Handoff - Projeto Painel RDO / Omada / EACE

Este documento contém o contexto essencial do projeto para que o próximo chat do Antigravity (ou qualquer desenvolvedor) possa continuar o trabalho exatamente de onde parou.

## 1. Arquitetura do Projeto
- **Robôs em Python (Exporters):** 
  - `rdo_omada_exporter` (Container): Coleta dados do portal da TP-Link Omada (Controladora principal).
  - `rdo_omada_exporter_st1` (Container): Coleta dados do portal Omada ST1.
  - `rdo_eace_os_exporter` (Container): Baixa a planilha de chamados do portal EACE via Selenium e dispara o script central `unificador_auto.py`.
- **Motor Central (`unificador_auto.py`):** Cruza os dados de escolas offline (do Omada) com os chamados abertos (do EACE). Ele formata os dados e gera um arquivo JSON de snapshot em `.streamlit/snapshots/<tenant>.json` (Ex: `bitnet.json`).
- **Dashboards (O projeto roda dois painéis simultâneos):** 
  1. **NOC Dashboard / Painel da NASA (`noc-dashboard`):** É o painel moderno (FastAPI + JS Vanilla) que estamos faturando e corrigindo o bug do S/N. O backend (`dashboard/api.py`) lê os snapshots JSON e o frontend (`dashboard/static/app.js`) renderiza a UI.
  2. **Site Web Clássico (`streamlit-web`):** Um painel secundário feito em Streamlit rodando na porta 8501. Ele compartilha a mesma pasta de volumes (`.streamlit`) mas a nossa prioridade de customização de UI é o Painel da NASA.
## 2. O Bug Atual a Ser Resolvido (Coluna Ticket "S/N")
**Sintoma:** Na tela de **"OS em Andamento"** no dashboard, a coluna "Ticket" insiste em exibir **S/N** (Sem Número), mesmo após o frontend já ter sido mapeado para ler `item['Ticket']` ou `item['Ticket#']`. 

**O que já foi feito / investigado:**
1. **Frontend (`app.js`):** A lógica está correta (`const ticket = item['Ticket'] || item['Ticket#'] || 'S/N';`). Se está exibindo S/N, é porque o JSON enviado pelo backend não contém o ticket ou ele vem como `null`/`NaN`.
2. **Backend (`unificador_auto.py`):**
   - O Python foi corrigido para lidar com colunas duplicadas no `pd.merge` usando `suffixes=('', '_drop')`.
   - Inserimos uma lógica dinâmica para encontrar qualquer coluna que contenha "ticket" no Excel da EACE e renomear para `Ticket#` (linhas 387-391 de `unificador_auto.py`).
   - Simulamos um *mock* do Pandas localmente e o merge das chaves `INEP` <-> `INEP_Extraido` funcionou, injetando o Ticket corretamente.
3. **A Descoberta Mais Recente:**
   - Foi confirmado via script de mock local que a planilha real (`controle_os_ri.xlsx`) **POSSUI** sim os tickets (Ex: INEP 22088008 tem o ticket 20260036809) e que a lógica do Pandas no `unificador_auto.py` consegue mesclar e injetar esse número perfeitamente no dicionário JSON.
   - *Ação recomendada para o novo chat:* Como a lógica do Pandas está 100% perfeita e os dados existem na planilha, a única razão para o frontend continuar mostrando "S/N" é que o novo JSON `bitnet.json` **não está sendo gerado/atualizado** pelo robô no ambiente de produção. O foco imediato deve ser analisar os logs do container (`docker compose logs --tail 50 rdo_eace_os_exporter`) para ver se o `unificador_auto.py` está sofrendo algum *crash* silencioso antes de salvar o arquivo JSON.
## 3. Próximas Implementações Pendentes (Backlog)
- **APK/PWA do Painel:** O usuário solicitou recentemente a possibilidade de transformar o dashboard em um APK para Android ou PWA (Progressive Web App). Isso deve ser planejado assim que a UI estiver 100% estabilizada.
- **Remoção da coluna "Causa" (Concluído):** A coluna Causa foi removida do HTML e do `renderRecoveries()` na tela de "Recuperações", mas preservada na tela "OS em Andamento". A UI já reflete isso.

## 4. Dicas e Infraestrutura (Docker)
- O projeto usa `docker-compose`. Qualquer alteração de arquivos HTML, CSS, ou JS estáticos exige o rebuild da imagem do dashboard:
  `docker compose up -d --build noc-dashboard`
- Se você (IA) alterar o `unificador_auto.py` ou robôs web, o rebuild precisa ser focado no exporter:
  `docker compose up -d --build rdo_eace_os_exporter`
- Os contêineres usam o Selenium. Para evitar erros de `session not created`, os robôs Omada e Eace foram ajustados para usarem o Chrome binário local `--headless` em vez do modo `--headless=new` nativo do SeleniumManager. Não altere os blocos `ChromeOptions` nestes robôs sem necessidade.

## 5. Arquivos Principais para Modificar
- **Coração lógico:** `unificador_auto.py`
- **Renderização da UI:** `dashboard/static/app.js` e `dashboard/static/index.html`
- **Raspador de Chamados:** `eace/eace_os_exporter.py` (baixa a planilha de controle_os_ri.xlsx).
