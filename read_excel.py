import pandas as pd
import json

path1 = r"c:\Users\ADM\Documents\NOC\Arquivos\Automação\RDO\omada.xlsx"
path2 = r"c:\Users\ADM\Documents\NOC\Arquivos\Automação\RDO\rdoatualizado1.xlsx"

def read_excel_info(path):
    xl = pd.ExcelFile(path)
    info = {"sheets": {}}
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        info["sheets"][sheet] = {
            "columns": list(df.columns),
            "head": df.head(3).to_dict(orient="records")
        }
    return info

print("OMADA:")
print(json.dumps(read_excel_info(path1), default=str, indent=2))
print("\nRDOATUALIZADO1:")
print(json.dumps(read_excel_info(path2), default=str, indent=2))
