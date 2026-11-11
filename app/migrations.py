"""
Tiny schema upgrader for existing databases.

New columns and unique constraints added after the original project are listed
here. `upgrade_schema()` adds whatever is missing (SQLite and MySQL), so an old
database keeps working without being recreated. It runs from `flask init-db`,
`flask upgrade-db` and run.py.

A hand-written list instead of Alembic: the project has one table set, a few
additive changes and must keep accepting the original MySQL dump. With
destructive or branching changes, Alembic (Flask-Migrate) would be the better tool.
"""
import logging

import sqlalchemy as sa

from .extensions import db
from .utils.timeslots import parse_slot

log = logging.getLogger(__name__)

# (table, column, SQL type + default) — only ever append to this list
NEW_COLUMNS = [
    ('doctors', 'days', "VARCHAR(50) DEFAULT ''"),
    ('doctor_bookings', 'status', "VARCHAR(20) DEFAULT 'booked'"),
    ('doctor_bookings', 'starts_at', 'TIME'),
    ('doctor_bookings', 'holds_slot', 'BOOLEAN DEFAULT 1'),
    ('facility_bookings', 'open_request', 'BOOLEAN DEFAULT 1'),
    ('users', 'archived', 'BOOLEAN NOT NULL DEFAULT 0'),
    ('users', 'session_version', 'INTEGER NOT NULL DEFAULT 0'),
    ('users', 'failed_logins', 'INTEGER NOT NULL DEFAULT 0'),
    ('users', 'locked_until', 'DATETIME'),
    ('hospitals', 'archived', 'BOOLEAN NOT NULL DEFAULT 0'),
    ('doctors', 'archived', 'BOOLEAN NOT NULL DEFAULT 0'),
    ('facilities', 'archived', 'BOOLEAN NOT NULL DEFAULT 0'),
]

# Filled in right after the column is added (existing rows get the column default first).
BACKFILL = {
    'doctor_bookings.holds_slot': "UPDATE doctor_bookings SET holds_slot = NULL WHERE status = 'cancelled'",
    'facility_bookings.open_request': 'UPDATE facility_bookings SET open_request = NULL WHERE status <> 0',
}

# (index name, table, columns) — unique constraints that tables created before them do not have
NEW_UNIQUE_INDEXES = [
    ('uq_doctor_bookings_active_slot', 'doctor_bookings', ('doctor_id', 'date', 'slot', 'holds_slot')),
    ('uq_facility_bookings_open', 'facility_bookings', ('user_id', 'facility_id', 'service', 'open_request')),
    ('uq_users_email', 'users', ('email',)),
]


def _unique_column_sets(inspector, table):
    sets = {tuple(c['column_names']) for c in inspector.get_unique_constraints(table)}
    sets |= {tuple(i['column_names']) for i in inspector.get_indexes(table) if i.get('unique')}
    return sets


def _columns(inspector, table):
    return {c['name'] for c in inspector.get_columns(table)}


def _add_unique_indexes(inspector, tables):
    """Create missing unique indexes. Existing duplicates make one fail: that is logged, the rest still run."""
    created = []
    for name, table, columns in NEW_UNIQUE_INDEXES:
        if (table not in tables or not set(columns) <= _columns(inspector, table)
                or columns in _unique_column_sets(inspector, table)):
            continue
        try:
            db.session.execute(sa.text(f'CREATE UNIQUE INDEX {name} ON {table} ({", ".join(columns)})'))
            db.session.commit()
            created.append(name)
        except sa.exc.DBAPIError as exc:
            db.session.rollback()
            log.warning('Could not create unique index %s: existing rows break it (%s). Remove the duplicate '
                        'rows, then run `flask upgrade-db` again.', name, exc.orig)
    return created


def _backfill_start_times():
    """starts_at for bookings saved before the column existed (plain SQL: works on any old table layout)."""
    update = sa.text('UPDATE doctor_bookings SET starts_at = :t WHERE id = :id').bindparams(
        sa.bindparam('t', type_=sa.Time))
    for booking_id, slot in db.session.execute(sa.text('SELECT id, slot FROM doctor_bookings '
                                                       'WHERE starts_at IS NULL')).all():
        parsed = parse_slot(slot)
        if parsed is not None:
            db.session.execute(update, {'t': parsed, 'id': booking_id})


def upgrade_schema():
    """Add missing columns and unique indexes. Returns what was added ('table.column' / index names).

    Needs an app context.
    """
    inspector = sa.inspect(db.engine)
    tables = set(inspector.get_table_names())
    added = []
    for table, column, ddl in NEW_COLUMNS:
        if table not in tables:
            continue  # create_all() will create it with every column
        existing = {c['name'] for c in inspector.get_columns(table)}
        if column not in existing:
            db.session.execute(sa.text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))
            key = f'{table}.{column}'
            if key in BACKFILL:
                db.session.execute(sa.text(BACKFILL[key]))
            added.append(key)
    db.session.commit()
    inspector = sa.inspect(db.engine)
    if 'doctor_bookings' in tables and {'slot', 'starts_at'} <= _columns(inspector, 'doctor_bookings'):
        _backfill_start_times()
        db.session.commit()
    added += _add_unique_indexes(inspector, tables)
    return added
