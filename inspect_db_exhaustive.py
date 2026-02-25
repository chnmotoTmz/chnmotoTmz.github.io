import sqlite3
import os

db_path = 'instance/integration.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    q = 'みゆき'
    print(f"Searching for all occurrences of '{q}' in hatena_blog_entries...")
    
    cursor.execute("PRAGMA table_info(hatena_blog_entries);")
    cols = [col[1] for col in cursor.fetchall()]
    
    where_clauses = [f"{col} LIKE ?" for col in cols]
    query = f"SELECT * FROM hatena_blog_entries WHERE {' OR '.join(where_clauses)};"
    
    cursor.execute(query, [f'%{q}%'] * len(cols))
    matches = cursor.fetchall()
    
    if matches:
        print(f"Found {len(matches)} matches:")
        for m in matches:
            # Map columns to values
            row_dict = dict(zip(cols, m))
            print(f"\n--- MATCH ---")
            print(f"BlogID: {row_dict.get('blog_id')}")
            print(f"Title: {row_dict.get('title')}")
            print(f"Updated: {row_dict.get('updated')}")
            print(f"Categories: {row_dict.get('categories')}")
            # Print which column matched
            for col, val in row_dict.items():
                if val and q in str(val):
                    print(f"MATCH in column [{col}]: {str(val)[:200]}")
    else:
        print("No matches found.")
    conn.close()
