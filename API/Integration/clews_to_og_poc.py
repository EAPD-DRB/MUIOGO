import pandas as pd
from pathlib import Path
import json

def poc_pivot_clews_data(csv_path: str, variable_id: str = "ANC"):
    
    #Proof of Concept: In-memory ETL transformation for CLEWS to OG-Core.
    #Demonstrates pivoting long-format RYT data into a time-series matrix.
    
    print(f"[*] Extracting data from {csv_path}...")
    try:
        
        df = pd.read_csv(csv_path)
        value_column = df.columns[-1] 
        print("[*] Pivoting RYT data into time-series matrix")
        matrix = df.pivot_table(
            index='y', 
            columns='t', 
            values=value_column, 
            aggfunc='sum'
        ).fillna(0)
        matrix.index.name = 'Year'
        print("\n[+] In-Memory Matrix Ready for OG-Core Ingestion")
        print(matrix.head())
        return matrix
    
    except Exception as e:
        print(f"[!] Error: {e}")
        return None