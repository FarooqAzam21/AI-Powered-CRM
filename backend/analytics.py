import pandas as pd
import os

FILE = "tickets.csv"

def load_tickets():
    if not os.path.exists(FILE):
        return pd.DataFrame()
    return pd.read_csv(FILE)

def get_kpis(df):
    return {
        "total_tickets": len(df),
        "high_priority": len(df[df["Priority"].str.contains("High", na=False)]),
        "avg_confidence": round(df["Confidence"].mean(), 2) if not df.empty else 0
    }
