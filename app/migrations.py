"""
Tiny schema upgrader for existing databases.

New columns added after the original project are listed here. `upgrade_schema()`
adds any that are missing (SQLite and MySQL), so an old database keeps working
without being recreated. It runs from `flask init-db`, `flask upgrade-db` and run.py.
"""
import sqlalchemy as sa

from .extensions import db

# (table, column, SQL type + default) — only ever append to this list
NEW_COLUMNS = [
    ('doctors', 'days', "VARCHAR(50) DEFAULT ''"),
    ('doctor_bookings', 'status', "VARCHAR(20) DEFAULT 'booked'"),
]


def upgrade_schema():
    """Add missing columns. Returns the list of 'table.column' that were added. Needs an app context."""
    inspector = sa.inspect(db.engine)
    tables = set(inspector.get_table_names())
    added = []
    for table, column, ddl in NEW_COLUMNS:
        if table not in tables:
            continue  # create_all() will create it with every column
        existing = {c['name'] for c in inspector.get_columns(table)}
        if column not in existing:
            db.session.execute(sa.text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
            added.append(f'{table}.{column}')
    db.session.commit()
    return added
