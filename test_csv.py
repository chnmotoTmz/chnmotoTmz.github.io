import csv
import os
genre_file = os.path.join('data', 'genre_prompts.csv')
print('Testing fixed CSV file...')
try:
    with open(genre_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        print('Headers:', reader.fieldnames)
        rows = list(reader)
        print('Number of rows:', len(rows))
        for i, row in enumerate(rows):
            genre = row.get('ジャンル', '').strip()
            keywords = row.get('キーワード', '').strip()
            prompt = row.get('プロンプト', '').strip()
            print(f'Row {i+1}: genre="{genre}", keywords="{keywords[:50]}...", prompt length={len(prompt)}')
            if not genre or not keywords or not prompt:
                print(f'  WARNING: Missing data in row {i+1}')
except Exception as e:
    print('Error:', e)