"""Start MediBook on this computer:  venv\\Scripts\\python run.py  (then open http://127.0.0.1:5000)."""
import os

from app import create_app
from app.seed import init_db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        init_db()   # first start: creates the tables and loads the sample data
    app.run(host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '5000')))
