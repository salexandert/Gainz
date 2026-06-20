from urllib.parse import urlparse

from flask import abort, current_app, render_template, redirect, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user
)

from ..extensions import db, login_manager
from . import blueprint
from .forms import LoginForm, CreateAccountForm
from .models import User

LOCAL_ADMIN_EMAIL = "admin@local.gainz"
SAFE_LOGIN_REDIRECTS = (
    ("/home", "home_blueprint.index"),
    ("/import_transactions", "import_transactions_blueprint.import_wizard"),
    ("/holdings_accounting", "holdings_accounting_blueprint.holdings_accounting"),
    ("/auto_link", "auto_link_blueprint.auto_link"),
    ("/stats", "stats_blueprint.index"),
    ("/tax_filing_review", "tax_filing_review_blueprint.index"),
    ("/model", "model_blueprint.index"),
    ("/export", "export_blueprint.index"),
    ("/history", "history_blueprint.index"),
    ("/add_links", "add_links_blueprint.add_links"),
    ("/privacy", "privacy_blueprint.index"),
    ("/setting/change_password", "setting_blueprint.change_password"),
)


@blueprint.route('/')
def route_default():
    return redirect(url_for('base_blueprint.login'))


# @blueprint.route('/<template>')
# @login_required
# def route_template(template):
#     return render_template(template + '.html')


@blueprint.route('/fixed_<template>')
@login_required
def route_fixed_template(template):
    return render_template('fixed/fixed_{}.html'.format(template))


@blueprint.route('/page_<error>')
def route_errors(error):
    return render_template('errors/page_{}.html'.format(error))

## Login & Registration


def _has_users():
    return db.session.query(User.id).first() is not None


def _is_local_request():
    return request.remote_addr in ("127.0.0.1", "::1", "localhost")


def _safe_next_endpoint(target):
    if not target:
        return None

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path or ""
    for prefix, endpoint in SAFE_LOGIN_REDIRECTS:
        if path == prefix or path.startswith(f"{prefix}/"):
            return endpoint

    return None


def _redirect_to_safe_login_next(default_endpoint='home_blueprint.index'):
    endpoint = _safe_next_endpoint(request.args.get('next')) or default_endpoint
    return redirect(url_for(endpoint))


@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm(request.form)
    create_form = CreateAccountForm(request.form)

    if not _has_users():
        if not _is_local_request():
            abort(403)

        admin_username = current_app.config['ADMIN']['username']
        if request.method == 'GET':
            create_form.username.data = admin_username

        status = ''
        if 'create_account' in request.form:
            username = (request.form.get('username') or '').strip()
            password = request.form.get('password') or ''

            if not username:
                status = 'Choose a username.'
            elif len(password) < 8:
                status = 'Use a password with at least 8 characters.'
            else:
                user = User(username=username, email=LOCAL_ADMIN_EMAIL, password=password)
                user.add_to_db()
                login_user(user)
                return _redirect_to_safe_login_next()

        return render_template(
            'login/login.html',
            login_form=login_form,
            create_form=create_form,
            setup_required=True,
            status=status,
        )

    if 'login' in request.form:
        user = User.query.filter_by(username=request.form['username']).first()
        if user:
            if user.checkpw(request.form['password']):
                login_user(user)
                return _redirect_to_safe_login_next()
            else:
                status = 'Password Error !'
        else:
            status = "User doesn't exist !"
        return render_template('login/login.html', login_form=login_form, create_form=create_form, status=status)

    if current_user.is_authenticated:
        return _redirect_to_safe_login_next()
    return render_template('login/login.html', login_form=login_form, create_form=create_form, status='')
   
@blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('base_blueprint.login'))


@blueprint.route('/shutdown')
def shutdown():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'Server shutting down...'

## Errors


@login_manager.unauthorized_handler
def unauthorized_handler():
    endpoint = request.endpoint or ""
    next_url = ""
    if endpoint and endpoint != "base_blueprint.login":
        try:
            next_url = url_for(endpoint)
        except Exception:
            next_url = ""
    return redirect(url_for('base_blueprint.login', next=next_url))


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('errors/page_403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('errors/page_404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('errors/page_500.html'), 500
