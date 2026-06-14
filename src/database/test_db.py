import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "processed" / "plantops.db"

def run_query(query: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    print("Machines:")
    for row in run_query("SELECT machine_id, machine_name, criticality FROM machine_master"):
        print(row)
    
    print("\nCritical alarms:")
    for row in run_query("""
                         SELECT machine_id, timestamp, alarm_code, message
                         FROM alarm_events
                         WHERE severity = 'critical'
                         """):
        print(row)