import sqlite3
import os

db_path = 'instance/integration.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

date_q = '2025-12-21'
print(f"Searching for entries on {date_q}...")
cursor.execute("SELECT title, updated, categories, blog_id FROM hatena_blog_entries WHERE updated LIKE ?;", (f'{date_q}%',))
matches = cursor.fetchall()
for m in matches:
    print(f"  Title: {m[0]}")
    print(f"  Updated: {m[1]}")
    print(f"  Categories: {m[2]}")
    print(f"  BlogID: {m[3]}")
    print("-" * 30)
    
conn.close()
