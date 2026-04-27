import sqlite3

conn = sqlite3.connect('database.db')

# Users table
conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        skills TEXT
    )
''')

# Jobs table - isme skills column hai
conn.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        skills TEXT NOT NULL,
        description TEXT NOT NULL,
        posted_by INTEGER
    )
''')
# Applications table - Apply button ke liye
conn.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        job_id INTEGER,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (job_id) REFERENCES jobs (id)
    )
''')
conn.commit()
conn.close()
print("Database ready! Users aur Jobs dono table ban gaye ✅")