from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField

## login and registration


class add_user_Form(FlaskForm):
    username = StringField('Username', id='username_create')
    email = StringField('Email')
    password = PasswordField('Password', id='pwd_create')

class delete_user_Form(FlaskForm):
    username = StringField('Username', id='username_delete')

class setting_password_Form(FlaskForm):
    username = StringField('Username', id='username_setting')
    password = PasswordField('Password', id='pwd_setting')

class change_password_Form(FlaskForm):
    origin_password = PasswordField('Current password', id='current_password')
    new_password = PasswordField('New password', id='new_password')
    new_password2 = PasswordField('Confirm new password', id='confirm_new_password')
