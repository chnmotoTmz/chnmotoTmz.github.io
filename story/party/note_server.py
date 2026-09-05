from flask import Flask, jsonify, request, send_from_directory
import os
import subprocess
import yaml
import json

app = Flask(__name__)

BASE_DIR = r"c:\Users\motoc\story\party"
ARTICLES_DIR = os.path.join(BASE_DIR, "articles")

# Serve static files from the base directory
@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'note_manager.html')

@app.route('/api/articles')
def list_articles():
    if not os.path.exists(ARTICLES_DIR):
        return jsonify([])
    
    articles = []
    # Sort files to show newest first (based on prefix 091, 090...)
    files = sorted([f for f in os.listdir(ARTICLES_DIR) if f.endswith('.md')], reverse=True)
    for f in files:
        path = os.path.join(ARTICLES_DIR, f)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                title = f.replace('.md', '')
                thumbnail = None
                date = ""
                
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        meta = yaml.safe_load(parts[1])
                        title = meta.get('title', title)
                        thumbnail = meta.get('thumbnail')
                        date = meta.get('date', "")
                
                # Get first few lines of body text
                body_text = content.split('---')[-1].strip()
                preview = body_text[:120].replace('\n', ' ') + "..."
                
                articles.append({
                    "filename": f,
                    "title": title,
                    "preview": preview,
                    "thumbnail": thumbnail,
                    "date": date
                })
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    return jsonify(articles)

@app.route('/api/run/<script_name>')
def run_script(script_name):
    scripts = {
        "capture": "capture_note_session.py",
        "scrape": "scrape_note.py"
    }
    if script_name not in scripts:
        return jsonify({"status": "error", "message": "Invalid script"}), 400
    
    script_path = os.path.join(BASE_DIR, scripts[script_name])
    if not os.path.exists(script_path):
        return jsonify({"status": "error", "message": f"Script {scripts[script_name]} not found"}), 404
        
    # Run in background to not block the server
    subprocess.Popen(["python", script_path], cwd=BASE_DIR)
    return jsonify({"status": "success", "message": f"{script_name.capitalize()} process started in a new window."})

@app.route('/api/post', methods=['POST'])
def post_article():
    data = request.json
    filename = data.get('filename')
    path = os.path.join(ARTICLES_DIR, filename)
    
    if not os.path.exists(path):
        return jsonify({"status": "error", "message": "File not found"}), 404
        
    script_path = os.path.join(BASE_DIR, "post_to_note.py")
    
    # post_to_note might open a browser, so run as Popen or check result
    try:
        # For post_to_note, we might want to wait for it or just fire and forget
        # Given it might take 10-20s, background is better but we lose immediate feedback
        # Let's run it and capture the process
        subprocess.Popen(["python", script_path, path], cwd=BASE_DIR)
        return jsonify({"status": "success", "message": f"Posting {filename} to Note draft... Check the new browser window."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/articles/<path:filename>')
def serve_thumbnail(filename):
    return send_from_directory(ARTICLES_DIR, filename)

if __name__ == '__main__':
    print("Starting Note Manager Server on http://localhost:5000")
    app.run(port=5000)
