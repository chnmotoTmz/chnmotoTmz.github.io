import sqlite3
import os

db_path = 'instance/integration.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    keywords = ['みゆき', '津田', '名探偵']
    
    for q in keywords:
        print(f"\nSearching for keyword: {q}")
        # Search in hatena_blog_entries
        cursor.execute("SELECT blog_id, title, hatena_entry_id, updated, categories FROM hatena_blog_entries WHERE title LIKE ? OR categories LIKE ?;", (f'%{q}%', f'%{q}%'))
        matches = cursor.fetchall()
        if matches:
            for m in matches:
                print(f"  [Match in DB] BlogID: {m[0]} | Title: {m[1]} | Updated: {m[3]} | Categories: {m[4]} | ID: {m[2]}")
        else:
            print("  No matches found.")
            
    conn.close()
