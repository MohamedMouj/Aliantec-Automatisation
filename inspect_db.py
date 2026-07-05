import sqlite3
conn = sqlite3.connect('Aliantec/db.sqlite3')
cur = conn.cursor()
print(cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name like 'analytics_%'").fetchall())
print(cur.execute("PRAGMA table_info(analytics_executionlog)").fetchall())
