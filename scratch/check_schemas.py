import sqlite3

def get_columns(db_path, table_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info([{table_name}])")
    columns = [(row[1], row[2]) for row in cursor.fetchall()]
    conn.close()
    return columns

tables = ["questions", "personalities", "answers", "scores"]
for table in tables:
    cols_django = get_columns("db.sqlite3", table)
    cols_flask = get_columns("2takukun_web-main/instance/database.db", table)
    print(f"Table: {table}")
    print(f"  Django: {cols_django}")
    print(f"  Flask : {cols_flask}")
    if cols_django == cols_flask:
        print("  MATCH")
    else:
        print("  !!! MISMATCH !!!")
