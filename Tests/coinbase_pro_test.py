import pandas as pd
import os
from ast import literal_eval
from time import strftime
from openpyxl import load_workbook
import base64
import datetime
import io
import pandas as pd
from time import strftime
import os
from ast import literal_eval
from assets import Asset
import sys
import pathlib
import dateutil
from utils import *
import math
from transaction import Buy, Receive, Sell, Send, Receive, Transaction

df = pd.read_csv('coinbase_pro_account_11_15_21.csv')

import ipdb

sells = []
buys = []
links = []
highest_index = 0



for index,row in df.iterrows():

    if index <= highest_index:
        continue

    if index == 0:
        continue
    

    quantity = None
    amount_in_usd = None
    symbol = None
    fee = None
    timestamp = None
    buy = None
    sell = None

    trade_id = str(row['trade id'])
    pre_trans_type = row['type']
    
    timestamp = row['time']
    print(timestamp)

    if pre_trans_type != 'match':
        continue

    if row['amount/balance unit'] == 'USD' and row['type'] == 'match':
        amount_in_usd = row['amount']
        # print(amount_in_usd)
        
    elif row['amount/balance unit'] == 'USD' and row['type'] == 'fee':
        fee = row['amount']
        
    else:
        quantity = row['amount']
        symbol = row['amount/balance unit']
        # print(f"{symbol} Quantity {quantity} ")
        
    i = 1
    while (index + i <= df.index[-1]) and str(df.loc[index + i]['trade id']) == trade_id:
        
        highest_index = index + i
        # print(f'sub looping {highest_index}')
        
        if df.loc[index + i]['amount/balance unit'] == 'USD' and df.loc[index + i]['type'] == 'match':
            amount_in_usd = row['amount']
            # print(f"Amount In USD {amount_in_usd}")
            

        elif df.loc[index + i]['amount/balance unit'] == 'USD' and df.loc[index + i]['type'] == 'fee':
            fee = row['amount']
            
        else:

            quantity = df.loc[index + i]['amount']
            symbol = df.loc[index + i]['amount/balance unit']

            # print(f' Quantity {quantity}')

        i += 1

        if quantity is not None and amount_in_usd is not None and symbol is not None:
            # print('got all ')
            if amount_in_usd > 0:
                trans_type = "sell"
                usd_spot = abs(quantity) * abs(amount_in_usd)
                sell = Sell(symbol=symbol, quantity=abs(quantity), time_stamp=timestamp, usd_spot=usd_spot, source='test_file')
                sells.append(sell)
                
            else:
                trans_type = "buy"
                usd_spot = abs(quantity) * abs(amount_in_usd)
                buy = Buy(symbol=symbol, quantity=abs(quantity), time_stamp=timestamp, usd_spot=usd_spot, source='test_file')
                buys.append(buy)
            
            break
        

            
sells_df = pd.DataFrame([vars(s) for s in sells])
buys_df = pd.DataFrame([vars(s) for s in buys])