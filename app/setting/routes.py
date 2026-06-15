from . import blueprint
from flask import render_template, current_app, request, redirect
from flask_login import login_required, current_user
from .forms import add_user_Form, delete_user_Form, change_password_Form, setting_password_Form
from ..base.models import User, is_local_admin


def _local_email_for_username(username):
    return f"{username}@local.gainz"

@blueprint.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_User():
    admin_user = current_app.config['ADMIN']['username']
    if is_local_admin(current_user, admin_user):
        form = add_user_Form(request.form)
        if 'Add' in request.form:
            username = (request.form.get('username') or '').strip()
            user = User.query.filter_by(username=username).first()
            if user :
                status = 'Username is existing'
            else:
                User(
                    username=username,
                    email=_local_email_for_username(username),
                    password=request.form['password'],
                ).add_to_db()
                status = 'Add user success !'
            return render_template('add_user.html', form = form, status = status)
        return render_template('add_user.html', form = form, status = '')
    return redirect('/page_403')

@blueprint.route('/delete_user', methods=['GET', 'POST'])
@login_required
def delete_user():    
    admin_user = current_app.config['ADMIN']['username']
    if is_local_admin(current_user, admin_user):
        form = delete_user_Form(request.form)
        if 'Delete' in request.form:
            username = request.form['username']
            user = User.query.filter_by(username=username).first()
            if user:
                if username == admin_user: 
                    status = "admin user can't be deleted !"
                else:
                    user.delete_from_db()
                    status = "delete user success !"
            else:
                status = "user doesn't exist !"
            return render_template('delete_user.html', form = form, status = status)
        return render_template('delete_user.html', form = form, status = '') 
    return redirect('/page_403')

@blueprint.route('/setting_password', methods=['GET', 'POST'])
@login_required
def setting_password():
    admin_user = current_app.config['ADMIN']['username']
    if is_local_admin(current_user, admin_user):
        form = setting_password_Form(request.form)
        if 'Setting' in request.form:
            username = request.form['username']
            user = User.query.filter_by(username=username).first()
            if user:
                if username == admin_user: 
                    status = "please change admin password from server !"
                else:
                    user.password = user.hashpw(request.form['password'])
                    user.db_commit()
                    status = "Setting password success !"
            else:
                status = "user doesn't exist !"
            return render_template('setting_password.html', form = form, status = status)
        return render_template('setting_password.html', form = form, status = '') 
    return redirect('/page_403')

@blueprint.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = change_password_Form(request.form)
    if request.method == 'POST':
        user = User.query.filter_by(username=current_user.username).first()
        current_password = request.form.get('origin_password', '')
        new_password = request.form.get('new_password', '')
        confirmed_password = request.form.get('new_password2', '')

        status_type = 'danger'
        if not user:
            status = "Could not find the signed-in account. Please log out and sign back in."
        elif not user.checkpw(current_password):
            status = "Current password does not match."
        elif not new_password:
            status = "Enter a new password."
        elif len(new_password) < 8:
            status = "Use at least 8 characters for the new password."
        elif new_password != confirmed_password:
            status = "New password and confirmation do not match."
        else:
            user.password = user.hashpw(new_password)
            user.db_commit()
            status = "Password updated successfully."
            status_type = 'success'

        return render_template(
            'change_password.html',
            form=form,
            status=status,
            status_type=status_type,
        )
    return render_template('change_password.html', form=form, status='', status_type='')
