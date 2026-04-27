import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

print("Purane columns check kar raha hu...")

# Pehle dekh kya columns hain
cursor.execute("PRAGMA table_info(jobs)")
columns = [col[1] for col in cursor.fetchall()]
print("Abhi ke columns:", columns)

# Naye columns add kar
new_cols = ['location', 'salary', 'skills', 'description']

for col in new_cols:
    if col not in columns:
        cursor.execute(f'ALTER TABLE jobs ADD COLUMN {col} TEXT')
        print(f"✅ {col} column add ho gaya")
    else:
        print(f"⚠️ {col} already hai")

conn.commit()
conn.close()
print("\n🎉 Database ready! Ab python app.py chala")