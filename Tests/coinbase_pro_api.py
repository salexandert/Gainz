# First import the libraries that we need to use
import pandas as pd
import requests
import json
from utils import fetch_crypto_price
import dateutil
import datetime
from transaction import Buy,Sell
from threading import Thread
import concurrent.futures
import time

if __name__ == "__main__":
    # we set which pair we want to retrieve data for
    timestamp = dateutil.parser.parse('2020-09-24T11:59:17.404Z')
    # timestamp = timestamp.replace(tzinfo=None)
    threads = []
    transactions = []
    for i in range(100):

        timestamp = timestamp + datetime.timedelta(days=1)
        trans = Buy('BTC', 1, timestamp, 0.0, 'api_test')
        transactions.append(trans)
        new_thread = Thread(target=fetch_crypto_price, args=(trans,))
        threads.append(new_thread)
        

    for t in threads:
        time.sleep(.2)
        t.start()
        
    for t in threads:
        t.join()



    # import ipdb 
    # ipdb.set_trace()