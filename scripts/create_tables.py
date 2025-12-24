import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app_factory import create_app
from src.database import db

app = create_app()
with app.app_context():
    print('Creating tables...')
    db.create_all()
    print('Tables created')
