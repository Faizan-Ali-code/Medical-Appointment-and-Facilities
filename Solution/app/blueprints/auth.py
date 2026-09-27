"""Login, registration and logout."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import func

from ..extensions import db
from ..models import User
from ..utils import form_values
from ..utils.auth import login_user, logout_user

bp = Blueprint('auth', __name__)

REGISTER_FIELDS = ('name', 'email', 'password', 'phone', 'city')


def find_user_by_email(email):
    return db.session.scalar(db.select(User).where(func.lower(User.email) == email.strip().lower()))


def password_problem(password):
    """Return an error message if the password is too weak, else None."""
    minimum = current_app.config['MIN_PASSWORD_LENGTH']
    if len(password) < minimum:
        return f'Password must be at least {minimum} characters.'
    return None


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form = form_values('email', 'password')
        user = find_user_by_email(form['email'])
        if user and user.check_password(form['password']):
            db.session.commit()  # saves the hash if an old plain-text password was upgraded
            login_user(user)
            return redirect(url_for('account.account'))
        flash('Email or Password is Incorrect.', 'danger')
    return render_template('auth/login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = {}
    if request.method == 'POST':
        form = form_values(*REGISTER_FIELDS)
        form['email'] = form['email'].lower()
        problem = password_problem(form['password']) if form['password'] else None
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
            db.session.commit()
            flash('Congrats, Your Account Is Created. You can login now.', 'success')
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
