import sqlite3
import os

db_path = 'instance/integration.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

q = '津田'
cursor.execute("SELECT title, updated, categories, blog_id FROM hatena_blog_entries WHERE title LIKE ?;", (f'%{q}%',))
matches = cursor.fetchall()
print(f"Found {len(matches)} matches for '{q}':")
for m in matches:
    print(f"  Title: {m[0]} | Updated: {m[1]} | BlogID: {m[3]}")
    
conn.close()
