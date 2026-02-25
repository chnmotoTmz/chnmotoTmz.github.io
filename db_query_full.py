import sqlite3
import os

db_path = 'instance/integration.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Searching for title '津田'...")
cursor.execute("SELECT title, updated, categories, blog_id FROM hatena_blog_entries WHERE title LIKE '%津田%';")
matches = cursor.fetchall()
for m in matches:
    print(f"  Title: {m[0]}")
    print(f"  Updated: {m[1]}")
    print(f"  Categories: {m[2]}")
    print(f"  BlogID: {m[3]}")
    print("-" * 30)

print("\nSearching for title 'みゆき'...")
cursor.execute("SELECT title, updated, categories, blog_id FROM hatena_blog_entries WHERE title LIKE '%みゆき%' OR categories LIKE '%みゆき%';")
matches = cursor.fetchall()
for m in matches:
    print(f"  Title: {m[0]}")
    print(f"  Updated: {m[1]}")
    print(f"  Categories: {m[2]}")
    print(f"  BlogID: {m[3]}")
    print("-" * 30)
    
conn.close()
