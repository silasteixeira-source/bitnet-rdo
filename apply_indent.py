import sys
import os

with open('abrirChamado_selenium.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = lines[:387]

new_lines.append('                config_path = os.path.join(os.path.dirname(__file__), ".streamlit", "config_robo.json")\n')
new_lines.append('                inserir_nota = True\n')
new_lines.append('                try:\n')
new_lines.append('                    if os.path.exists(config_path):\n')
new_lines.append('                        import json\n')
new_lines.append('                        with open(config_path, "r", encoding="utf-8") as f:\n')
new_lines.append('                            config = json.load(f)\n')
new_lines.append('                        current_tenant = "st1" if "st1" in cache_path.lower() else "bitnet"\n')
new_lines.append('                        inserir_nota = config.get(current_tenant, {}).get("inserir_nota", True)\n')
new_lines.append('                except: pass\n\n')

new_lines.append('                if not inserir_nota:\n')
new_lines.append('                    logging.info(f"[{inep}] 7. INSERÇÃO DE NOTA BLOQUEADA pelo Dashboard. Ignorando preenchimento...")\n')
new_lines.append('                    sucesso_nota = True\n')
new_lines.append('                else:\n')
new_lines.append('                    logging.info(f"[{inep}] 7. Preenchendo MENSAGEM_NOTA...")\n')
new_lines.append('                    try:\n')

for line in lines[389:471]:
    new_lines.append('    ' + line)

new_lines.extend(lines[471:])

with open('abrirChamado_selenium.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
