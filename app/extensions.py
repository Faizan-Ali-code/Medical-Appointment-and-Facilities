"""Flask extensions, created here and bound to the app in create_app()."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
# Per-client-IP request limits (login, registration). Behind a reverse proxy, apply werkzeug's ProxyFix so the
# real client address is used instead of the proxy's.
limiter = Limiter(key_func=get_remote_address)
