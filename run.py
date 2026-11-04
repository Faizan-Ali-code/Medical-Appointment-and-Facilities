"""Start the development server:  venv\\Scripts\\python run.py"""
import os

from app import create_app
from app.extensions import db
from app.migrations import upgrade_schema

app = create_app()

# bring an older database up to date (adds new columns; never deletes data)
with app.app_context():
    db.create_all()
    for column in upgrade_schema():
        app.logger.warning('Database upgraded: added %s', column)

if __name__ == '__main__':
    app.run(host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '5000')))
