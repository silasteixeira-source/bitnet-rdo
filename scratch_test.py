import pandas as pd
import json

df = pd.DataFrame({'A': [pd.Timestamp('2026-08-01')], 'B': [1]})
df = df.fillna("")
d = df.to_dict(orient='records')

try:
    json.dumps(d)
    print("SUCCESS")
except Exception as e:
    print("ERROR:", type(e).__name__, e)
