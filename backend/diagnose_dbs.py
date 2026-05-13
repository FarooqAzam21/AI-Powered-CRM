import sqlite3
import os

def check_and_clear():
    dbs = ["app.db", "app_v2.db", "app_v3.db"]
    report = []
    
    for db in dbs:
        if not os.path.exists(db):
            report.append(f"{db}: Does not exist")
            continue
            
        try:
            conn = sqlite3.connect(db)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if cursor.fetchone():
                cursor.execute("SELECT email FROM users")
                emails = [r[0] for r in cursor.fetchall()]
                report.append(f"{db} users: {emails}")
                
                # Option to clear
                # cursor.execute("DELETE FROM users")
                # conn.commit()
            else:
                report.append(f"{db}: No 'users' table found")
            conn.close()
        except Exception as e:
            report.append(f"{db} error: {str(e)}")
            
    with open("db_report.txt", "w") as f:
        f.write("\n".join(report))
    print("Report written to db_report.txt")

if __name__ == "__main__":
    check_and_clear()
