from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
import sys

@blueprint.route('/',  methods=['GET'])
@login_required
def index():

    return render_template('home.html')