"""Register, log in and log out."""
from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from ..extensions import db
from ..forms import LoginForm, RegisterForm
from ..models import User
from ..utils import is_safe_path
from ..utils.auth import home_endpoint, login_user, logout_user

bp = Blueprint('auth', __name__)


def _after_login(user):
    """Back to the page that asked for the login (?next=), else the user's home page."""
    target = request.args.get('next')
    return redirect(target if is_safe_path(target) else url_for(home_endpoint(user)))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user:
        return redirect(url_for(home_endpoint(g.user)))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(db.select(User).filter_by(email=form.email.data))
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Welcome back, {user.name}.', 'success')
            return _after_login(user)
        flash('Wrong email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for(home_endpoint(g.user)))
    user = User(role=User.USER)
    form = RegisterForm(user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash(f'Welcome, {user.name}. Your account is ready.', 'success')
        return _after_login(user)
    return render_template('auth/register.html', form=form)


@bp.post('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))
