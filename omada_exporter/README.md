# Omada Cloud Data Exporter

Automatiza o acesso ao **TP-Link Omada Cloud** para exportar dados em formato XLSX periodicamente, com interface gráfica para controle.

---

## Requisitos

| Componente | Versão mínima | Observação |
|------------|--------------|------------|
| Python | 3.8+ | [Download](https://www.python.org/downloads/) |
| Google Chrome | Qualquer versão recente | Necessário para o Selenium |
| Selenium | 4.15+ | Instalado via pip |
| Tkinter | (vem com Python) | Inclua durante instalação do Python |

> **Atenção:** Ao instalar o Python no Windows, marque a opção **"Add Python to PATH"** e certifique-se de que o **tcl/tk** (tkinter) está habilitado.

---

## Instalação

### Windows

1. Extraia a pasta `omada_exporter` no seu computador
2. Abra o **Prompt de Comando** (cmd) ou **PowerShell**
3. Navegue até a pasta do programa:
   ```
   cd C:\caminho\para\omada_exporter
   ```
4. Instale a dependência:
   ```
   pip install selenium
   ```
5. Execute o programa:
   ```
   python omada_exporter.py
   ```

### Alternativa rápida (Windows)
- Dê duplo clique no arquivo **`iniciar.bat`**

### Linux
```bash
cd /caminho/para/omada_exporter
chmod +x iniciar.sh
./iniciar.sh
```

---

## Como Usar

### 1. Inicialização

Ao abrir o programa, a janela principal será exibida com os campos preenchidos:

| Campo | Valor padrão |
|-------|-------------|
| E-mail | noceace@bitinternet.com.br |
| Senha | (sua senha) |
| Intervalo | 30 segundos |
| Diretório | ./dados_omada/ |
| Arquivo | omada_dados.xlsx |

### 2. Configuração

- **Intervalo (s):** Define o tempo entre cada exportação. Mínimo recomendado: 15 segundos. Padrão: 30 segundos.
- **Diretório:** Escolha onde salvar o arquivo XLSX. Clique no botão **📂** para navegar.
- **Arquivo:** Nome do arquivo de saída. O padrão é `omada_dados.xlsx`. O arquivo é sempre **sobrescrito**, servindo como base de dados atualizada.

### 3. Iniciar

Clique em **▶ INICIAR EXPORTAÇÃO**. O programa irá:

1. Abrir o Google Chrome automaticamente
2. Acessar o portal Omada Cloud
3. Fazer login com as credenciais fornecidas
4. Clicar no botão **Exportar**
5. Baixar o arquivo XLSX para o diretório configurado
6. Renomear o arquivo para o nome padrão
7. Aguardar o intervalo configurado e repetir

### 4. Monitoramento

O **Log de Atividade** mostra todas as ações em tempo real:

- Login bem-sucedido
- Exportação concluída
- Erros e tentativas de recuperação
- Timestamps de cada evento

### 5. Parar

Clique em **■ PARAR** para interromper o loop. O browser será fechado automaticamente.

---

## Comportamento do Arquivo

- O arquivo **sempre é sobrescrito** na mesma localização
- A cada ciclo, o arquivo anterior é removido e o novo é colocado no lugar
- Isso permite que outros sistemas (Excel, Power BI, Python, etc.) leiam o arquivo como base de dados
- Se o arquivo estiver aberto em outro programa, o sistema tenta copiar em vez de renomear

---

## Resolução de Problemas

### "Browser não abre"
- Certifique-se de que o Google Chrome está instalado
- Na primeira execução, o Selenium pode baixar o ChromeDriver automaticamente

### "Botão Exportar não encontrado"
- Verifique se o portal Omada está acessível
- O programa salva um screenshot de debug na pasta `dados_omada/` para diagnóstico
- Verifique se a página carregou completamente (observe o log)

### "Sessão expirada"
- O programa detecta automaticamente quando o login expira e refaz o login
- Se o problema persistir, verifique as credenciais

### "Arquivo em uso"
- Feche o arquivo XLSX em outros programas (Excel, etc.)
- O programa tenta copiar o arquivo se o renome falhar

---

## Estrutura de Arquivos

```
omada_exporter/
├── omada_exporter.py    ← Programa principal
├── requirements.txt     ← Dependências Python
├── iniciar.bat          ← Launcher para Windows
├── iniciar.sh           ← Launcher para Linux
├── README.md            ← Este arquivo
└── dados_omada/         ← Pasta de downloads (criada automaticamente)
    └── omada_dados.xlsx ← Arquivo exportado
```

---

## Notas de Segurança

- As credenciais ficam salvas na memória durante a execução
- Não são armazenadas em nenhum arquivo
- O browser é fechado ao parar o programa
- Recomenda-se usar este programa em um computador seguro e confiável

---

## Licença

Uso interno para automação de processos. Distribuição restrita.
