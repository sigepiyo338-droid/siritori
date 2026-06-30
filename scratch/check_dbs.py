import sqlite3
import os

def check_db(path):
    print(f"=== {path} ===")
    if not os.path.exists(path):
        print("File does not exist.")
        return
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        for table in tables:
            try:
                cursor.execute(f"SELECT count(*) FROM [{table}]")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
            except Exception as e:
                print(f"  {table}: Error: {e}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

check_db("db.sqlite3")
