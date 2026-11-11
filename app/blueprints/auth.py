"""Login, registration and logout.

Brute-force protection works on two levels:
* per client IP: Flask-Limiter allows LOGIN_RATE_LIMIT POSTs to /login and /register;
* per account: LOGIN_MAX_FAILURES failed logins in a row lock the account for
  LOGIN_LOCK_MINUTES. The counter is incremented in one SQL UPDATE, so parallel
  attempts cannot lose increments, and the lock is temporary, so an attacker
  cannot lock a user out for good.
"""
import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, limiter
from ..models import User
from ..utils import form_values
from ..utils.auth import login_user, logout_user
from ..utils.passwords import password_problem

bp = Blueprint('auth', __name__)

REGISTER_FIELDS = ('name', 'email', 'password', 'phone', 'city')
LOGIN_FAILED = 'Email or Password is Incorrect.'
_dummy_hash = None


def _login_limit():
    return current_app.config['LOGIN_RATE_LIMIT']


def find_user_by_email(email):
    return db.session.scalar(db.select(User).where(func.lower(User.email) == email.strip().lower()))


def _waste_a_hash_check(password):
    """Spend the same time as a real check when the email is unknown, so timing does not reveal accounts."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = generate_password_hash('not-a-real-password',
                                             method=current_app.config['PASSWORD_HASH_METHOD'])
    check_password_hash(_dummy_hash, password)


def _record_failure(user):
    """Atomic increment; lock the account when the limit is reached."""
    db.session.execute(update(User).where(User.id == user.id).values(failed_logins=User.failed_logins + 1))
    db.session.refresh(user)
    if user.failed_logins >= current_app.config['LOGIN_MAX_FAILURES']:
        minutes = current_app.config['LOGIN_LOCK_MINUTES']
        user.locked_until = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        user.failed_logins = 0
    db.session.commit()


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit(_login_limit, methods=['POST'])
def login():
    if request.method == 'POST':
        form = form_values('email', 'password')
        user = find_user_by_email(form['email'])
        if user is None or user.archived:
            _waste_a_hash_check(form['password'])
        elif user.is_locked():
            flash(f'Too many failed attempts. This account is locked for up to '
                  f'{current_app.config["LOGIN_LOCK_MINUTES"]} minutes.', 'danger')
            return render_template('auth/login.html'), 429
        elif user.check_password(form['password']):
            user.failed_logins, user.locked_until = 0, None
            db.session.commit()  # also saves the hash if an old plain-text password was upgraded
            login_user(user)
            return redirect(url_for('account.account'))
        else:
            _record_failure(user)
        flash(LOGIN_FAILED, 'danger')
    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit(_login_limit, methods=['POST'])
def register():
    form = {}
    if request.method == 'POST':
        form = form_values(*REGISTER_FIELDS)
        form['email'] = form['email'].lower()
        problem = password_problem(form['password'], form['email'], form['name']) if form['password'] else None
        if not all(form.values()):
            flash('Please Fill All The Fields', 'warning')
        elif problem:
            flash(problem, 'warning')
        elif find_user_by_email(form['email']):
            flash('This Email Is Already In Use', 'danger')
        else:
            password = form.pop('password')
            user = User(**form, role='user')  # self-registration never creates admins
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:  # the same email registered a moment ago (unique constraint)
                db.session.rollback()
                flash('This Email Is Already In Use', 'danger')
                return render_template('auth/register.html', form=form)
            flash('Congrats, Your Account Is Created. You can login now.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
