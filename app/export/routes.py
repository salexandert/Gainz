from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from utils import *




@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def index():
    
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)

    return render_template('export.html', stats_table_data=stats_table_data)


@blueprint.route('/save',  methods=['POST'])
@login_required
def save():
    
    transactions = current_app.config['transactions']

    save_as_filename = transactions.export_to_excel()

    print(f"exporting to {save_as_filename}")

    return jsonify(save_as_filename)
    





