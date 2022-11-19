from . import blueprint
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from utils import *
from transactions import Transactions


@blueprint.route('/',  methods=['GET'])
@login_required
def index():
    
    transactions = current_app.config['transactions']
    stats_table_data = get_stats_table_data(transactions)

    saves = transactions.load_saves()

    
    return render_template('history.html', stats_table_data=stats_table_data, history=saves)



@blueprint.route('/load',  methods=['POST'])
@login_required
def load():
    
    transactions = current_app.config['transactions']

    filename = request.json['data'][0]

    transactions.load(filename)

    return jsonify("Yess")


@blueprint.route('/revert',  methods=['POST'])
@login_required
def revert():
    
    transactions = current_app.config['transactions']

    
    filename = request.json['data'][0]
    transactions.load(filename)
    transactions.save(f"Reverted to {filename}")

    return jsonify("Yess")


@blueprint.route('/delete',  methods=['POST'])
@login_required
def delete():
    
    transactions = current_app.config['transactions']

    filename = request.json['data'][0]
    transactions.delete(filename)

    transactions = Transactions()

    current_app.config['transactions'] = transactions

    return jsonify("Yess")