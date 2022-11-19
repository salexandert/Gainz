
import datetime
from transaction import Transaction
from dateutil.tz import tzutc
import dateutil
import requests
import datetime
import json
import ipdb 

import os

# xpub_address = 'xpub6CUGRUonZSQ4TWtTMmzXdrXDtypWKiKrhko4egpiMZbpiaQL2jkwSB1icqYh2cfDfVxdx4df189oLKnC5fSwqPfgyP3hooxujYzAu3fDVmz'

xpub_address = 'xpub6CKr5CEVFJQitTwdb9kfrEZBwTz6z7W3SE6cmzHCAr9NaxQmZXR8wtWiXcLTqm5d2y9yskQCo7ncFYawNaquRUqvQFdUFVPy47zAn3rqguc'

zpub_address = 'zpub6qkRsFkyW3YuZ1M1N46XZSf9pNU2xAmMwCZAMRBNx6qAC8A6LJ9iA1QCkBDPUtT32V2SvJ8Qcks6bKpght88FN9TAdU7p4za63nZd3TewxA'

        
url = f"https://blockchain.info/multiaddr?active={zpub_address}"
headers = {"Accept": "application/json"}
response =  requests.request("GET", url, headers=headers, timeout=1)


with open('response.txt', 'w') as f:
    json.dump(response.json(), f, indent=4)

# dict_keys(['addresses', 'wallet', 'txs', 'info', 'recommend_include_fee'])
# response.json()['txs'][0].keys()
# dict_keys(['hash', 'ver', 'vin_sz', 'vout_sz', 'size',
#  'weight', 'fee', 'relayed_by', 'lock_time', 'tx_index', 'double_spend', 'time', 'block_index', 'block_height', 'inputs', 'out', 'result', 'balance'])