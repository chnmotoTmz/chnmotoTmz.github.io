#!/bin/bash
set -e

echo "Starting Hatena Blog Suite..."

# RAG繝｢繝・Ν閾ｪ蜍募・蟄ｦ鄙・
echo "Training RAG model..."
python -c "
import pandas as pd
from src.rag import train_and_save_model
try:
    df = pd.read_csv('data/genre_prompts.csv')
    texts = df['繝励Ο繝ｳ繝励ヨ'].tolist()
    train_and_save_model(texts, 'genre_prompts')
    print('RAG model training completed successfully.')
except Exception as e:
    print(f'RAG model training failed: {e}')
    print('Continuing without RAG model...')
"

# 譛ｬ譚･縺ｮ繧｢繝励Μ襍ｷ蜍・
echo "Starting main application..."
exec python app.py
