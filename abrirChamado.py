import pandas as pd
import pyautogui
import time
import pyperclip

# --- 1. COORDENADAS (X, Y) ---
COORD_PESQUISA = (634, 246)
COORD_OPCAO_INEP = (651, 285)
COORD_NOVA_OS = (1128, 250)
COORD_ABRIR_OS = (477, 276)
COORD_ESPERAR_INCLUIR = (804, 389)
COORD_ENTRAR_OS = (300, 556)
COORD_NOTAS = (561, 531)
COORD_COLAR_NOTAS = (371, 614)
COORD_ADICIONAR_FINALIZAR = (852, 629)
COORD_VOLTAR = (71, 227)
COORD_REFRESH = (100, 56)

# --- 2. CONFIGURAÇÕES GERAIS ---
ARQUIVO_PLANILHA = "Chamados Pendentes (PA e MA) - Aprovados e Offline 2.xlsx"
MENSAGEM_NOTA = """Olá! Sou um dos analistas do Projeto Aprender Conectado (EACE), referente a escola.

Nosso sistema detectou que nosso equipamento está sem conexão. Saberia nos informar se a escola está sem internet ou se o equipamento foi desligado?

Poderia nos enviar uma foto dos aparelhos dentro do rack preto? Assim já verificamos se há algum erro físico nas conexões.

Coletando informações com o responsável da escola."""
LIMITE_DIARIO = 30

pyautogui.FAILSAFE = True 
pyautogui.PAUSE = 1.0 # Pausa automática após cada ação

def forcar_topo_da_pagina():
    """Força o navegador a voltar para a posição zero (topo)"""
    pyautogui.moveTo(10, 10)
    pyautogui.press('home')
    pyautogui.scroll(5000)
    time.sleep(2)

# --- LEITURA DA PLANILHA ---
df = pd.read_excel(ARQUIVO_PLANILHA)
if 'Status_Automacao' not in df.columns:
    df['Status_Automacao'] = ""

pendentes = df[df['Status_Automacao'] == ""].head(LIMITE_DIARIO)

if pendentes.empty:
    print("Todos os INEPs da planilha já possuem status definido!")
    exit()

print("VOCÊ TEM 10 SEGUNDOS PARA MAXIMIZAR A TELA DO SISTEMA...")
time.sleep(10)

# --- LOOP DE PROCESSAMENTO ---
for index, row in pendentes.iterrows():
    inep = str(row['INEP']).strip()
    print(f"\nProcessando INEP: {inep}")
    
    # 1. Pesquisar na barra principal
    pyautogui.click(COORD_PESQUISA[0], COORD_PESQUISA[1])
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(inep, interval=0.15)
    time.sleep(3)
    
    # 2. Clicar na opção do INEP colado
    pyautogui.click(COORD_OPCAO_INEP[0], COORD_OPCAO_INEP[1])
    time.sleep(6) 
    
    print(f"[{inep}] Iniciando criação da OS...")
    
    # ZERA A TELA ANTES DE CLICAR
    forcar_topo_da_pagina()
    
    # 3. Adicionar Nova OS
    pyautogui.click(COORD_NOVA_OS[0], COORD_NOVA_OS[1])
    time.sleep(4)
    
    # 4. ABRIR OS - TENTATIVAS COM ESPAÇOS AMPLOS
    print(f"[{inep}] Preenchendo INEP no modal - Tentativa 1")
    pyautogui.click(COORD_ABRIR_OS[0], COORD_ABRIR_OS[1])
    time.sleep(1.5)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(inep, interval=0.15)
    time.sleep(6) 
    pyautogui.press('down')
    time.sleep(1.5)
    pyautogui.press('enter')
    time.sleep(3)
    
    print(f"[{inep}] Preenchendo INEP no modal - Tentativa 2")
    pyautogui.click(COORD_ABRIR_OS[0], COORD_ABRIR_OS[1])
    time.sleep(1.5)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(inep, interval=0.15)
    time.sleep(7) 
    pyautogui.press('down')
    time.sleep(1.5)
    pyautogui.press('enter')
    time.sleep(3)

    print(f"[{inep}] Preenchendo INEP no modal - Tentativa 3")
    pyautogui.click(COORD_ABRIR_OS[0], COORD_ABRIR_OS[1])
    time.sleep(1.5)
    pyautogui.hotkey('ctrl', 'a')
    pyautogui.press('backspace')
    pyautogui.write(inep, interval=0.15)
    time.sleep(7) 
    pyautogui.press('down')
    time.sleep(1.5)
    pyautogui.press('enter')
    time.sleep(3)
    
    # 5. Esperar o clique de inclusão
    pyautogui.click(COORD_ESPERAR_INCLUIR[0], COORD_ESPERAR_INCLUIR[1])
    time.sleep(8)
    
    # ZERA A TELA NOVAMENTE ANTES DE PROSSEGUIR
    forcar_topo_da_pagina()
    
    # 6. Entrar na OS
    pyautogui.click(COORD_ENTRAR_OS[0], COORD_ENTRAR_OS[1])
    time.sleep(5)
    
    # 7. Notas
    pyautogui.click(COORD_NOTAS[0], COORD_NOTAS[1])
    time.sleep(3)
    
    # 8. Colar notas
    pyautogui.click(COORD_COLAR_NOTAS[0], COORD_COLAR_NOTAS[1])
    pyperclip.copy(MENSAGEM_NOTA)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(3)
    
    # 9. Adicionar para finalizar
    pyautogui.click(COORD_ADICIONAR_FINALIZAR[0], COORD_ADICIONAR_FINALIZAR[1])
    time.sleep(4)
    
    df.at[index, 'Status_Automacao'] = "OS Aberta e Nota Inserida"
    print(f"[{inep}] Sucesso!")
    
    # 10. Voltar pra finalizar
    pyautogui.click(COORD_VOLTAR[0], COORD_VOLTAR[1])
    time.sleep(4)
    
    # 11. Refresh na página 
    pyautogui.click(COORD_REFRESH[0], COORD_REFRESH[1])
    
    # PAUSA FINAL DO CICLO: Aguarda de 10 a 15 segundos (definido para 12 segundos)
    print(f"[{inep}] Ciclo finalizado. Aguardando intervalo de respiro...")
    time.sleep(12)

# --- SALVA RESULTADOS ---
df.to_excel(ARQUIVO_PLANILHA, index=False)
print("\nFinalizado! Planilha salva.")