# Regras e Memória do Projeto: BITNET RDO & Automação NOC

Este arquivo define o contexto, a arquitetura e as regras de negócio deste projeto para que qualquer agente Antigravity (em qualquer máquina ou sessão) entenda instantaneamente o funcionamento do sistema.

## 1. Visão Geral da Arquitetura
O sistema é uma aplicação multiplataforma desenvolvida em **Streamlit** para automação de chamados, relatórios e controle operacional do NOC (Omada, RDO, OS).
- **Página Principal de Fluxo Unificado**: `pages/4_Unificador_Omada_Chamados.py`
  - Cruzamento de 4 bases de entrada: **Omada Antigo**, **Omada Novo**, **Controle de OS** e **RDO**.
  - 4 abas/tabelas de saída: `Falta_Abrir_Chamado`, `Ja_Aberto`, `Fechar_Chamado`, `Ignorados_Ou_Sem_INEP`.

## 2. Regras de Negócio e Tratamento de Dados
1. **Enriquecimento Oficial com Nome da Escola (Base EACE)**:
   - A função `get_escolas_eace_map()` lê a planilha do Google Sheets EACE (`1Onw1vaSO2SIQ_OfAoDPI6ycnXWTAZ2ijhtujAOhI9UM`, aba `EACE`).
   - Mapeia Código INEP (coluna D) -> Nome da Escola (coluna E).
   - Coluna `Nome da Escola` fica em todas as tabelas logo após `INEP_Extraido`.
2. **Remoção de Colunas Não Operacionais (Case-Insensitive)**:
   - Colunas do Omada (`DESCRIPTION`, `TYPE`, `MODEL`, `CUSTOMER NUMBER`, `SITE NUMBER`, `DEVICE NUMBER`, `ALERT NUMBER`, `ROLE`, `ROLES`) devem sempre ser removidas.
3. **Regra das 4 Horas Offline**:
   - Em `Falta_Abrir_Chamado`, a coluna `Regra de Abertura (4h Offline)` avalia tempo de queda e sinaliza `? PODE ABRIR (>4h)` ou `? AGUARDAR (<4h)`.
4. **Carimbo de Fuso Horário de Brasília**:
   - Todas as tabelas têm a coluna `Atualizado Em` no fuso **UTC-3 (Horário de Brasília)** (`DD/MM/YYYY HH:MM:SS`).

## 3. Segurança e Git
- **NUNCA** commitar `.streamlit/secrets.toml`, arquivos `.db`, `.xlsx/.xls`, ou senhas/credenciais hardcoded.
