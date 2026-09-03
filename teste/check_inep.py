import pandas as pd
inep = '21289930'
print(f'Procurando INEP {inep} nas planilhas do teste...')
try:
    df_omada = pd.read_excel('teste/OrganizationList_2026-09-03-13-26.xlsx')
    omada_match = df_omada[df_omada.apply(lambda row: inep in str(row.values), axis=1)]
    if not omada_match.empty:
        print('1. Encontrado no Omada Atual! Status e Uptime:')
        for _, row in omada_match.iterrows():
            print(f"   - Nome: {row.get('NAME', 'N/A')}")
            print(f"   - Status: {row.get('STATUS', 'N/A')}")
    else:
        print('1. NAO encontrado na planilha do Omada Atual.')
        
    df_rdo = pd.read_excel('teste/RDOST1.xlsx')
    rdo_match = df_rdo[df_rdo.apply(lambda row: inep in str(row.values), axis=1)]
    if not rdo_match.empty:
        print('2. Encontrado na planilha RDO!')
    else:
        print('2. NAO encontrado na planilha RDO.')
        
    df_os = pd.read_excel('teste/controle_OS.xlsx')
    os_match = df_os[df_os.apply(lambda row: inep in str(row.values), axis=1)]
    if not os_match.empty:
        print('3. Encontrado na planilha de OS (EACE)! Status da OS:')
        for _, row in os_match.iterrows():
            print(f"   - Ticket: {row.get('Ticket#', 'N/A')} // Status: {row.get('Status', 'N/A')}")
    else:
        print('3. NAO encontrado na planilha de OS.')
        
except Exception as e:
    print('Erro:', e)
