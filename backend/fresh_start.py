import os
import shutil

def fresh_start():
    print("🧹 Starting fresh start process...")
    
    # 1. Clean up old databases
    dbs = ["app.db", "app_v2.db", "app_v3.db", "db_report.txt"]
    for db in dbs:
        if os.path.exists(db):
            try:
                os.remove(db)
                print(f"✅ Deleted old file: {db}")
            except:
                print(f"⚠️ Could not delete {db} (it might be open in another process)")

    # 2. Setup data folder
    if not os.path.exists("data"):
        os.makedirs("data")
        print("✅ Created 'data' folder")
    
    # 3. Clean up the new data folder if it had old files
    new_db = "data/app.db"
    if os.path.exists(new_db):
        try:
            os.remove(new_db)
            print(f"✅ Reset fresh database: {new_db}")
        except:
             print(f"⚠️ Could not reset {new_db}")

    print("\n✨ DONE! Your system is now clean and ready.")
    print("👉 Please restart your backend with: uvicorn main:app --reload")

if __name__ == "__main__":
    fresh_start()
