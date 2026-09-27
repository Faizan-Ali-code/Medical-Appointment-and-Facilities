"""HTTP layer. Each module is one Flask blueprint."""
from . import account, admin, auth, bookings, public

ALL = [public.bp, auth.bp, account.bp, bookings.bp, admin.bp]
