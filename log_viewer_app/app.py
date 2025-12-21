from flask import Flask, render_template, request, jsonify
import os
import json

app = Flask(__name__)
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs', 'posts')

@app.route('/')
def index():
    files = [f for f in os.listdir(LOG_DIR) if f.endswith('.jsonl')]
    return render_template('index.html', files=files)

@app.route('/view_log')
def view_log():
    filename = request.args.get('filename')
    if not filename or not filename.endswith('.jsonl'):
        return jsonify({'error': 'Invalid filename'}), 400
    path = os.path.join(LOG_DIR, filename)
    if not os.path.exists(path):
        return jsonify({'error': 'File not found'}), 404
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                entry = json.loads(line)
                entries.append(entry)
            except Exception:
                continue
    return jsonify({'entries': entries})

if __name__ == '__main__':
    app.run(debug=True)
