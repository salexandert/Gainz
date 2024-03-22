# Before Whole new auto link


from conversion import Conversion
from transaction import Buy, Receive, Sell, Send, Receive
import pandas as pd
import os
from time import strftime
from openpyxl import load_workbook
import base64
import datetime
import io
import pandas as pd
import os
from assets import Asset
import sys
import dateutil
from utils import *
import math
import time
import threading


whois_timezone_info = {
        "A": 1 * 3600,
        "ACDT": 10.5 * 3600,
        "ACST": 9.5 * 3600,
        "ACT": -5 * 3600,
        "ACWST": 8.75 * 3600,
        "ADT": 4 * 3600,
        "AEDT": 11 * 3600,
        "AEST": 10 * 3600,
        "AET": 10 * 3600,
        "AFT": 4.5 * 3600,
        "AKDT": -8 * 3600,
        "AKST": -9 * 3600,
        "ALMT": 6 * 3600,
        "AMST": -3 * 3600,
        "AMT": -4 * 3600,
        "ANAST": 12 * 3600,
        "ANAT": 12 * 3600,
        "AQTT": 5 * 3600,
        "ART": -3 * 3600,
        "AST": 3 * 3600,
        "AT": -4 * 3600,
        "AWDT": 9 * 3600,
        "AWST": 8 * 3600,
        "AZOST": 0 * 3600,
        "AZOT": -1 * 3600,
        "AZST": 5 * 3600,
        "AZT": 4 * 3600,
        "AoE": -12 * 3600,
        "B": 2 * 3600,
        "BNT": 8 * 3600,
        "BOT": -4 * 3600,
        "BRST": -2 * 3600,
        "BRT": -3 * 3600,
        "BST": 6 * 3600,
        "BTT": 6 * 3600,
        "C": 3 * 3600,
        "CAST": 8 * 3600,
        "CAT": 2 * 3600,
        "CCT": 6.5 * 3600,
        "CDT": -5 * 3600,
        "CEST": 2 * 3600,
        "CET": 1 * 3600,
        "CHADT": 13.75 * 3600,
        "CHAST": 12.75 * 3600,
        "CHOST": 9 * 3600,
        "CHOT": 8 * 3600,
        "CHUT": 10 * 3600,
        "CIDST": -4 * 3600,
        "CIST": -5 * 3600,
        "CKT": -10 * 3600,
        "CLST": -3 * 3600,
        "CLT": -4 * 3600,
        "COT": -5 * 3600,
        "CST": -6 * 3600,
        "CT": -6 * 3600,
        "CVT": -1 * 3600,
        "CXT": 7 * 3600,
        "ChST": 10 * 3600,
        "D": 4 * 3600,
        "DAVT": 7 * 3600,
        "DDUT": 10 * 3600,
        "E": 5 * 3600,
        "EASST": -5 * 3600,
        "EAST": -6 * 3600,
        "EAT": 3 * 3600,
        "ECT": -5 * 3600,
        "EDT": -4 * 3600,
        "EEST": 3 * 3600,
        "EET": 2 * 3600,
        "EGST": 0 * 3600,
        "EGT": -1 * 3600,
        "EST": -5 * 3600,
        "ET": -5 * 3600,
        "F": 6 * 3600,
        "FET": 3 * 3600,
        "FJST": 13 * 3600,
        "FJT": 12 * 3600,
        "FKST": -3 * 3600,
        "FKT": -4 * 3600,
        "FNT": -2 * 3600,
        "G": 7 * 3600,
        "GALT": -6 * 3600,
        "GAMT": -9 * 3600,
        "GET": 4 * 3600,
        "GFT": -3 * 3600,
        "GILT": 12 * 3600,
        "GMT": 0 * 3600,
        "GST": 4 * 3600,
        "GYT": -4 * 3600,
        "H": 8 * 3600,
        "HDT": -9 * 3600,
        "HKT": 8 * 3600,
        "HOVST": 8 * 3600,
        "HOVT": 7 * 3600,
        "HST": -10 * 3600,
        "I": 9 * 3600,
        "ICT": 7 * 3600,
        "IDT": 3 * 3600,
        "IOT": 6 * 3600,
        "IRDT": 4.5 * 3600,
        "IRKST": 9 * 3600,
        "IRKT": 8 * 3600,
        "IRST": 3.5 * 3600,
        "IST": 5.5 * 3600,
        "JST": 9 * 3600,
        "K": 10 * 3600,
        "KGT": 6 * 3600,
        "KOST": 11 * 3600,
        "KRAST": 8 * 3600,
        "KRAT": 7 * 3600,
        "KST": 9 * 3600,
        "KUYT": 4 * 3600,
        "L": 11 * 3600,
        "LHDT": 11 * 3600,
        "LHST": 10.5 * 3600,
        "LINT": 14 * 3600,
        "M": 12 * 3600,
        "MAGST": 12 * 3600,
        "MAGT": 11 * 3600,
        "MART": 9.5 * 3600,
        "MAWT": 5 * 3600,
        "MDT": -6 * 3600,
        "MHT": 12 * 3600,
        "MMT": 6.5 * 3600,
        "MSD": 4 * 3600,
        "MSK": 3 * 3600,
        "MST": -7 * 3600,
        "MT": -7 * 3600,
        "MUT": 4 * 3600,
        "MVT": 5 * 3600,
        "MYT": 8 * 3600,
        "N": -1 * 3600,
        "NCT": 11 * 3600,
        "NDT": 2.5 * 3600,
        "NFT": 11 * 3600,
        "NOVST": 7 * 3600,
        "NOVT": 7 * 3600,
        "NPT": 5.5 * 3600,
        "NRT": 12 * 3600,
        "NST": 3.5 * 3600,
        "NUT": -11 * 3600,
        "NZDT": 13 * 3600,
        "NZST": 12 * 3600,
        "O": -2 * 3600,
        "OMSST": 7 * 3600,
        "OMST": 6 * 3600,
        "ORAT": 5 * 3600,
        "P": -3 * 3600,
        "PDT": -7 * 3600,
        "PET": -5 * 3600,
        "PETST": 12 * 3600,
        "PETT": 12 * 3600,
        "PGT": 10 * 3600,
        "PHOT": 13 * 3600,
        "PHT": 8 * 3600,
        "PKT": 5 * 3600,
        "PMDT": -2 * 3600,
        "PMST": -3 * 3600,
        "PONT": 11 * 3600,
        "PST": -8 * 3600,
        "PT": -8 * 3600,
        "PWT": 9 * 3600,
        "PYST": -3 * 3600,
        "PYT": -4 * 3600,
        "Q": -4 * 3600,
        "QYZT": 6 * 3600,
        "R": -5 * 3600,
        "RET": 4 * 3600,
        "ROTT": -3 * 3600,
        "S": -6 * 3600,
        "SAKT": 11 * 3600,
        "SAMT": 4 * 3600,
        "SAST": 2 * 3600,
        "SBT": 11 * 3600,
        "SCT": 4 * 3600,
        "SGT": 8 * 3600,
        "SRET": 11 * 3600,
        "SRT": -3 * 3600,
        "SST": -11 * 3600,
        "SYOT": 3 * 3600,
        "T": -7 * 3600,
        "TAHT": -10 * 3600,
        "TFT": 5 * 3600,
        "TJT": 5 * 3600,
        "TKT": 13 * 3600,
        "TLT": 9 * 3600,
        "TMT": 5 * 3600,
        "TOST": 14 * 3600,
        "TOT": 13 * 3600,
        "TRT": 3 * 3600,
        "TVT": 12 * 3600,
        "U": -8 * 3600,
        "ULAST": 9 * 3600,
        "ULAT": 8 * 3600,
        "UTC": 0 * 3600,
        "UYST": -2 * 3600,
        "UYT": -3 * 3600,
        "UZT": 5 * 3600,
        "V": -9 * 3600,
        "VET": -4 * 3600,
        "VLAST": 11 * 3600,
        "VLAT": 10 * 3600,
        "VOST": 6 * 3600,
        "VUT": 11 * 3600,
        "W": -10 * 3600,
        "WAKT": 12 * 3600,
        "WARST": -3 * 3600,
        "WAST": 2 * 3600,
        "WAT": 1 * 3600,
        "WEST": 1 * 3600,
        "WET": 0 * 3600,
        "WFT": 12 * 3600,
        "WGST": -2 * 3600,
        "WGT": -3 * 3600,
        "WIB": 7 * 3600,
        "WIT": 9 * 3600,
        "WITA": 8 * 3600,
        "WST": 14 * 3600,
        "WT": 0 * 3600,
        "X": -11 * 3600,
        "Y": -12 * 3600,
        "YAKST": 10 * 3600,
        "YAKT": 9 * 3600,
        "YAPT": 10 * 3600,
        "YEKST": 6 * 3600,
        "YEKT": 5 * 3600,
        "Z": 0 * 3600,
}

if getattr(sys, 'frozen', False):
    basedir = os.path.dirname(sys.executable)
elif __file__:
    basedir = os.path.dirname(__file__)

class Transactions:

    def __init__(self, view=None):
        self.revision_num = None
        self.saves = self.load_saves()
        self.index = 0
        self.conversions = []
        self.asset_objects = []
        
        if view is not None:
            self.transactions = self.load(view)
            self.view = view
        
        elif len(self.saves) > 0:
            highest_rev = 0
            view = None
            revision_num = None

            for save in self.saves:
                if save['revision_num'] is None:
                    revision_num = 0
                else:
                    if save['revision_num'] > highest_rev:
                        highest_rev = save['revision_num']
                        view = save['value']
            
            print(f"the highest rev is {highest_rev}")

            if view is None:
                view = self.saves[-1]['value']
            
            self.transactions = self.load(view)
            self.view = view
        else:
            self.view = ""
            self.transactions = []
            self.revision_num = 0

    def __len__(self):
        return len(self.transactions)

    def __iter__(self):
        self.index = 0
        return self
    
    def __next__(self):
        try:
            result = self.transactions[self.index]
        except IndexError:
            raise StopIteration
        
        self.index += 1
        return result

    @property
    def links(self):
        links = set([
                link 
                for trans in self.transactions
                for link in trans.links
                ])
        
        return links

    def auto_link(self, algo, asset=None, min_link=0.000001, pre_check=False, year=None):
        """
        Automatically links buy and sell transactions based on the specified algorithm.

        Args:
            algo (str): The algorithm to use for linking transactions. Possible values are 'fifo', 'filo', 'min_gain_long', and 'min_gain'.
            asset (str, optional): The symbol of the asset to link. If provided, only transactions with the specified symbol will be considered for linking. Defaults to None.
            min_link (float, optional): The minimum link quantity. Transactions with a link quantity less than this value will be skipped. Defaults to 0.000001.
            pre_check (bool, optional): Whether to perform a pre-check before linking transactions. Defaults to False.
            year (int, optional): The year to filter transactions. Only transactions within the specified year will be considered for linking. Defaults to None.

        Returns:
            None
        """
        
        sells = {}
        buys = {}
        min_unlinked = 0.0000001

        # failures is a list of dicts
        failures = []

        # Sort into Buys a Sells
        for trans in self.transactions:

            # If asset is provided only auto-link symbol provided
            if asset is not None:
                if trans.symbol != asset:
                    continue

            if trans.trans_type == 'buy':

                if trans.symbol not in buys.keys():
                    buys[trans.symbol] = []

                buys[trans.symbol].append(trans)

            elif trans.trans_type == 'sell':
                
                if trans.symbol not in sells.keys():
                    sells[trans.symbol] = []

                sells[trans.symbol].append(trans)

            # Filter sales to a specific year
            if year is not None:
                date_range = {
                    'start_date': f"01/01/{year} 12:00 AM",
                    'end_date': f"12/31/{year} 11:59 PM"
                    }

                start_date = datetime.datetime.strptime(date_range['start_date'], "%m/%d/%Y %H:%M %p")
                end_date = datetime.datetime.strptime(date_range['end_date'], "%m/%d/%Y %H:%M %p")
                                                                        
                # Filter Transactions to date range
                for key in sells.keys():
                    filtered_transactions = []
                    for trans in sells[key]:

                        if trans.time_stamp >= start_date and trans.time_stamp <= end_date:              
                            filtered_transactions.append(trans)

                    sells[key] = filtered_transactions
                
        # sort for algo types
        if algo == 'fifo':
            # sort buys and sells by time_stamp
            for key in buys.keys():
                buys[key].sort(key=lambda x: x.time_stamp)
            
            for key in sells.keys():
                sells[key].sort(key=lambda x: x.time_stamp)

            keys = list(sells.keys())
            keys.sort()
            # Loop all Asset_types (keys)
            for key in keys:
                quantity_linked = 0.0

                links = []

                # loop sells to find link candidate
                for sell in sells[key]:
    
                    # check if sell has remaining unlinked quantity
                    if sell.unlinked_quantity > min_unlinked:
                        
                        #loop buys to find link candidate
                        for buy in buys[key]:

                            link_quantity = None

                            # break if sell has no remaining unlinked quantity
                            if sell.unlinked_quantity <= min_unlinked:
                                break

                            # Skip if buy has no remaining unlinked quantity
                            if buy.unlinked_quantity <= min_unlinked:
                                continue
                                                    
                            # check if buy came before sell
                            if buy.time_stamp >= sell.time_stamp:
                                continue

                            # Link 
                            # if sell unlinked is greater than buy unlinked, link quantity equals buy unlinked
                            if sell.unlinked_quantity >= buy.unlinked_quantity:
                                link_quantity = buy.unlinked_quantity
                            
                            # if sell unlinked is less than buy unlinked, link quantity equals sell unlinked
                            elif sell.unlinked_quantity <= buy.unlinked_quantity: 
                                link_quantity = sell.unlinked_quantity
                            
                            # print(f"\nthe link quantity BEFORE being rounded down [{link_quantity}] len {len(str(link_quantity))}")

                            # Set max length of link 
                            link_quantity = round_decimals_down(link_quantity)

                            # print(f"the link quantity after being rounded down [{link_quantity}] len {len(str(link_quantity))}")

                            # Determine link profitability
                            buy_price = link_quantity * buy.usd_spot
                            sell_price = link_quantity * sell.usd_spot
                            profit = sell_price - buy_price

                            # if the link is less than $1.00 skip it
                            if abs(profit) < 1.0:
                                # print(f"Skipping link because profit/loss [{profit} is less than $1.0]")
                                continue
                            
                            link = sell.link_transaction(buy, link_quantity)
                            links.append(link)
                            quantity_linked += link.quantity

                        if (sell.unlinked_quantity * sell.usd_spot) > min_unlinked:
                            # print(f"Sell Unlinkable when using [{algo}] symbol [{sell.symbol}] unlinkable_quantity [{sell.unlinked_quantity}]")
                            failures.append({
                                'asset': sell.symbol, 
                                'unlinkable': sell.unlinked_quantity,
                                'quantity': sell.quantity,
                                'timestamp': sell.time_stamp,
                                'algo': algo
                            })
        
        elif algo == 'filo':

            for key in buys.keys():
                buys[key].sort(key=lambda x: x.time_stamp, reverse=True)
            
            for key in sells.keys():
                sells[key].sort(key=lambda x: x.time_stamp)

            keys = list(sells.keys())
            keys.sort()
            
            for key in keys:
                quantity_linked = 0.0
                links = []

                for sell in sells[key]:
                    # check if sell has remaining unlinked quantity
                    if sell.unlinked_quantity > min_unlinked:
                        for buy in buys[key]:
                            link_quantity = None

                            # break if sell has no remaining unlinked quantity
                            if sell.unlinked_quantity <= min_unlinked:
                                break

                            # Skip if buy has no remaining unlinked quantity
                            if buy.unlinked_quantity <= min_unlinked:
                                continue

                            # check if buy came before sell
                            if buy.time_stamp >= sell.time_stamp:
                                continue

                            # Link 
                            # if sell unlinked is greater than buy unlinked, link quantity equals buy unlinked
                            if sell.unlinked_quantity >= buy.unlinked_quantity:
                                link_quantity = buy.unlinked_quantity

                            # if sell unlinked is less than buy unlinked, link quantity equals sell unlinked
                            elif sell.unlinked_quantity <= buy.unlinked_quantity: 
                                link_quantity = sell.unlinked_quantity

                            # Set max length of link 
                            link_quantity = round_decimals_down(link_quantity)

                            # Determine link profitability
                            buy_price = link_quantity * buy.usd_spot
                            sell_price = link_quantity * sell.usd_spot
                            profit = sell_price - buy_price

                            # if the link is less than 1 dollar skip it
                            if abs(profit) < 1.0:
                                continue

                            link = sell.link_transaction(buy, link_quantity)
                            links.append(link)
                            quantity_linked += link.quantity

                        if (sell.unlinked_quantity * sell.usd_spot) > min_unlinked:
                            print(f"Sell Unlinkable when using [{algo}] symbol [{sell.symbol}] unlinkable_quantity [{sell.unlinked_quantity}]")
                            failures.append({
                                'asset': sell.symbol, 
                                'unlinkable': sell.unlinked_quantity,
                                'quantity': sell.quantity,
                                'timestamp': sell.time_stamp,
                                'algo': algo
                            })

        elif algo == 'min_gain_long':
            for key in buys.keys():
                buys[key].sort(key=lambda x: x.time_stamp)
            
            for key in sells.keys():
                sells[key].sort(key=lambda x: x.time_stamp)
                sells[key].sort(key=lambda x: x.unlinked_quantity)
                sells[key].sort(key=lambda x: x.usd_spot)

            keys = list(sells.keys())
            keys.sort()
            for key in keys:
                quantity_linked = 0.0
                
                links = []
                for sell in sells[key]:
                                        
                    # break if sell has no remaining unlinked quantity
                    if sell.unlinked_quantity <= min_unlinked:
                        continue
                    
                    min_gain_long_batch = []
                    potential_sale_quantity = sell.unlinked_quantity
                    potential_sale_usd_spot = sell.usd_spot
                    min_gain_long_batch_gain = 0.0
                    min_gain_long_batch_quantity = 0.0
                    
                    # Linkable Buys Long
                    linkable_buys_long = [
                    trans for trans in self.transactions
                        if trans.trans_type == "buy"
                        and trans.symbol == key
                        and (sell.time_stamp > trans.time_stamp)
                        and (sell.time_stamp - trans.time_stamp).days > 365
                        and trans.unlinked_quantity > min_unlinked
                    ]

                    # Min Gain Long Batch
                    # print(f"items in linkable long {len(linkable_buys_long)}")
                    linkable_buys_long.sort(key=lambda trans: trans.usd_spot, reverse=True)
                    
                    target_quantity = potential_sale_quantity
                    
                    # loop linkable buys to find link candidate 
                    for trans in linkable_buys_long:
                        
                        buy_unlinked_quantity = trans.unlinked_quantity
                        
                        # Determine max link quantity
                        if target_quantity <= buy_unlinked_quantity:
                            link_quantity = target_quantity
                        
                        elif target_quantity >= buy_unlinked_quantity:
                            link_quantity = buy_unlinked_quantity

                        link_quantity = round_decimals_down(link_quantity)
                        target_quantity -= link_quantity

                        # Skip if gain or loss less than .01
                        cost_basis = link_quantity * float(trans.usd_spot)
                        proceeds = link_quantity * potential_sale_usd_spot
                        gain_or_loss = proceeds - cost_basis
                        
                        if abs(gain_or_loss) < 0.01:
                            continue

                        min_gain_long_batch_gain += gain_or_loss
                        min_gain_long_batch_quantity += link_quantity

                        min_gain_long_batch.append([trans, link_quantity])
                        
                        if target_quantity <= min_unlinked:
                            break
                    
                    for i in min_gain_long_batch:
                        link = sell.link_transaction(i[0], i[1])
                        links.append(link)
                        quantity_linked += link.quantity
            
            print(f"added {quantity_linked}")   

        elif algo == 'min_gain':
            # need to link all short sells with zero or less gain. then link long sells by min gain. then link anything left over.
            quantity_linked = 0.0

            for key in buys.keys():
                buys[key].sort(key=lambda x: x.time_stamp)
                buys[key].sort(key=lambda x: x.usd_spot)
            
            for key in sells.keys():
                sells[key].sort(key=lambda x: x.time_stamp)
                sells[key].sort(key=lambda x: x.unlinked_quantity)
                sells[key].sort(key=lambda x: x.usd_spot, reverse=True)

            keys = list(sells.keys())
            keys.sort()
            for key in keys:
                links = []

                for sell in sells[key]:
                                        
                    # break if sell has no remaining unlinked quantity
                    if sell.unlinked_quantity <= min_unlinked:
                        continue

                    min_gain_batch = []
                    potential_sale_quantity = sell.unlinked_quantity
                    target_quantity = potential_sale_quantity
                    potential_sale_usd_spot = sell.usd_spot

                    # All Linkable Buys 
                    linkable_buys = [
                            trans for trans in buys[key]
                            if trans.trans_type == "buy"
                            and trans.symbol == key
                            and (sell.time_stamp > trans.time_stamp)
                            and trans.unlinked_quantity > min_unlinked
                    ]

                    linkable_buys.sort(key=lambda trans: trans.usd_spot, reverse=True)

                    for trans in linkable_buys:
                        buy_unlinked_quantity = trans.unlinked_quantity
                        
                        # Determine max link quantity
                        if target_quantity <= buy_unlinked_quantity:
                            link_quantity = target_quantity
                        
                        elif target_quantity >= buy_unlinked_quantity:
                            link_quantity = buy_unlinked_quantity

                        link_quantity = round_decimals_down(link_quantity)
                        target_quantity -= link_quantity

                        #determine if we should skip link 
                        cost_basis = link_quantity * float(trans.usd_spot)
                        proceeds = link_quantity * potential_sale_usd_spot
                        gain_or_loss = proceeds - cost_basis
                        if abs(gain_or_loss) < 0.01:
                            continue

                        min_gain_batch.append([trans, round_decimals_down(link_quantity)])

                        if target_quantity <= min_unlinked:
                            break
                    
                    for i in min_gain_batch:
                        link = sell.link_transaction(i[0], i[1])
                        links.append(link)
                        quantity_linked += link.quantity
            
            
            print(f"added {quantity_linked}")
                               
        if pre_check:
            for trans in self.transactions:
                if asset is not None:
                    if trans.symbol != asset:
                        continue
                
                for link in links:
                    for trans_link in trans.links:
                        if link is trans_link:
                            trans.links.remove(trans_link)

        
        return failures
                            

    def convert_buys_to_lost(self, asset, amount):
        # method used to deal with crypto not sold on exchange but no longer in possession

        if asset in self.assets:
            
            # list of buys that were converted to lost
            buys_to_delete = []
            
            # what we want to calc
            bought = 0.0
            quantity_of_buys_converted_to_lost = 0.0

            for trans in self.transactions:
                if trans.symbol != asset:
                    continue

                if trans.trans_type == 'buy':
                    bought += trans.quantity


            for trans in self.transactions:
                if trans.symbol != asset:
                    continue
                
                if amount > 0 and trans.quantity <= amount and trans.trans_type == 'buy':
                    # Convert buy to lost
                  
                    conversion = Conversion(input_trans_type='buy', 
                                            output_trans_type='lost', 
                                            input_symbol=asset, 
                                            input_quantity=trans.quantity, 
                                            input_time_stamp=trans.time_stamp, 
                                            input_usd_spot=trans.usd_spot, 
                                            input_usd_total=trans.usd_total, 
                                            reason="Current HODL Buy to lost/deleted")
                    
                    self.conversions.append(conversion)
                
                    buys_to_delete.append(trans)

                    quantity_of_buys_converted_to_lost += trans.quantity


        for trans in self.transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()

        
        # print(f" Num of transactions to delete {len(buys_to_delete)} ")
        # print(f" Num of transactions before delete {len(self.transactions)} ")
        

        for trans in buys_to_delete:
            self.transactions.remove(trans)

    
        # print(f" Num of transactions after delete {len(self.transactions)} ")
        
        # what we want to calc a second time
        bought_after = 0.0

        for trans in self.transactions:
            if trans.symbol != asset:
                continue

            if trans.trans_type == 'buy':
                bought_after += trans.quantity

    
        print(f"AFTER CONVERSION bought {bought_after} {asset}")


    

    def convert_sends_to_sells(self, asset, amount_to_convert):
        # method used to deal with crypto not sold on exchange but no longer in possession
        ##### Sort these

        if asset in self.assets:
            
            # list of sends that were converted to sells
            sends = []
            sells = []
            sends_to_delete = []

            # what we want to calc
            sent = 0.0
            sold = 0.0
            bought = 0.0
            received = 0.0
            quantity_of_sends_converted_to_sells = 0.0
            inital_amount_to_convert = amount_to_convert

            self.transactions.sort(key=lambda x: x.time_stamp)

            for trans in self.transactions:
                if trans.symbol != asset:
                    continue

                if trans.trans_type == "sell":
                    sold += trans.quantity
                    continue
        
                if trans.trans_type == "buy":
                    bought += trans.quantity
                    continue

                if trans.trans_type == 'receive':
                    received += trans.quantity
                    continue

                # if trans.trans_type != 'send':
                #     continue

                if amount_to_convert > 0 and trans.quantity <= amount_to_convert and trans.trans_type == 'send':

                    if type(trans.usd_spot) != float:
                        print(f"skipping transaction {trans.name} because no usd_spot")
                        continue
                    
                    # Check if converting send to sell can be covered by buys
                    # if_send_is_converted = sold + trans.quantity
                    # difference = bought - if_send_is_converted

                    # if difference < 0:
                    #     if received < difference:
                    #         continue

                    sell = Sell(symbol=trans.symbol, quantity=trans.quantity, time_stamp=trans.time_stamp, usd_spot=trans.usd_spot, linked_transactions=trans.linked_transactions, source="Gainz App Send to Sale")

                    self.transactions.append(sell)


                    auto_link_failures = self.auto_link(asset=asset, algo='fifo', pre_check=True)
                    auto_link_failures.extend(self.auto_link(asset=asset, algo='filo', pre_check=True))
                    
                    if len(auto_link_failures) > 0:
                        self.transactions.remove(sell)
                        del(sell)
                        continue

                    # elif len(auto_link_failures) > 1:
                    #     print('More than 1 failures we done messed up!')


                    sold += sell.quantity

                    conversion = Conversion(input_trans_type='send', 
                                            output_trans_type='sell', 
                                            input_symbol=asset, 
                                            input_quantity=trans.quantity, 
                                            input_time_stamp=trans.time_stamp, 
                                            input_usd_spot=trans.usd_spot, 
                                            input_usd_total=trans.usd_total, 
                                            reason="Current HODL Send to Sell", 
                                            source=f"{trans.source} Converted in Gainz App")

                    self.conversions.append(conversion)
                    
                    sends_to_delete.append(trans)

                    quantity_of_sends_converted_to_sells += trans.quantity
                    
                    amount_to_convert -= trans.quantity


        for trans in self.transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()
        
        # print(f"\n\nSuccessfully Converted {quantity_of_sends_converted_to_sells} in Sends to Sells in {len(sends_to_delete)} transactions!!\n\n")
        # print(f" Num of transactions to delete {len(sends_to_delete)} ")
        # print(f" Num of transactions before delete {len(self.transactions)} ")
        
        for trans in sends_to_delete:
            self.transactions.remove(trans)

        # print(f" Num of transactions after delete {len(self.transactions)} ")
        
        # what we want to calc a second time
        bought_after = 0.0
        sold_after = 0.0
        sent_after = 0.0

        for trans in self.transactions:
            if trans.symbol != asset:
                continue

            if trans.trans_type == 'buy':
                bought_after += trans.quantity

            elif trans.trans_type == 'sell':
                sold_after += trans.quantity
            
            elif trans.trans_type == 'send':
                sent_after += trans.quantity

        # print(f"AFTER CONVERSION Sold {sold_after} {asset}")
        # print(f"AFTER CONVERSION Sent {sent_after} {asset}")
        # print(f"AFTER CONVERSION Unaccounted for {amount_to_convert} {asset}")


        return f"\nSuccessfully Converted {quantity_of_sends_converted_to_sells} in Sends to Sells in {len(sends_to_delete)} transactions!!\n"


    def convert_receives_to_buys(self, asset, amount_to_convert):
        # method used to deal with crypto not sold on exchange but no longer in possession

        if asset in self.assets:
            
            # List of Receives Converted
            receives_to_delete = []
            
            # what we want to calc
            received = 0.0
            quantity_of_receives_converted_to_buys = 0.0

            for trans in self.transactions:
                if trans.symbol != asset:
                    continue

                if trans.trans_type == 'receive':
                    received += trans.quantity


            for trans in self.transactions:
                if trans.symbol != asset:
                    continue

                # if trans.trans_type == 'receive':
                    # print(f" Candidate Found for Receive to Buy!!! {trans.name} {trans.quantity} ")
                    # print(amount_to_convert)
                
                if amount_to_convert > 0 and amount_to_convert <= amount_to_convert and trans.trans_type == 'receive':
                    # Convert receive to buy

                    

                    buy = Buy(symbol=trans.symbol, quantity=trans.quantity, time_stamp=trans.time_stamp, usd_spot=trans.usd_spot, linked_transactions=trans.linked_transactions, source="Gainz App Receive to Buy")
                  
                    conversion = Conversion(input_trans_type='receive', 
                                            output_trans_type='buy', 
                                            input_symbol=asset, 
                                            input_quantity=trans.quantity, 
                                            input_time_stamp=trans.time_stamp, 
                                            input_usd_spot=trans.usd_spot, 
                                            input_usd_total=trans.usd_total, 
                                            reason="Current HODL Receive to buy")
                    
                    self.conversions.append(conversion)

                    self.transactions.append(buy)
                
                    receives_to_delete.append(trans)

                    quantity_of_receives_converted_to_buys += trans.quantity


        for trans in self.transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()

        
        # print(f" Num of transactions to delete {len(receives_to_delete)} ")
        # print(f" Num of transactions before delete {len(self.transactions)} ")
        

        for trans in receives_to_delete:
            self.transactions.remove(trans)

    
        # print(f" Num of transactions after delete {len(self.transactions)} ")
        
        # what we want to calc a second time
        bought_after = 0.0

        for trans in self.transactions:
            if trans.symbol != asset:
                continue

            if trans.trans_type == 'buy':
                bought_after += trans.quantity

    
        print(f"AFTER CONVERSION bought {bought_after} {asset}")



    def load_saves(self):

        saves = []
        revision_num = None
        match_object = "saved_"

        view_num = 1
        for root, dirs, files in os.walk(os.path.join(basedir, 'saves')):
            for f in files:

                save_as_filename = os.path.join(basedir, 'saves', f)

                if match_object in f and f.endswith('xlsx'):
                    workbook = load_workbook(filename=save_as_filename)
                    if 'Description' in workbook.sheetnames:
                        sheet = workbook['Description']
                        description = sheet.cell(column=1, row=1).value
                        revision_num = sheet.cell(column=2, row=1).value

                    else:
                        description = ""
                    
                    saves.append({'label': save_as_filename, 'value': save_as_filename, 'description': description, 'revision_num': revision_num})
                    view_num += 1

        self.saves = saves
        
        return saves

    @property    
    def assets(self):

        assets = set()
    
        for trans in self.transactions:
            assets.add(trans.symbol)

        return assets

    # Load Previous Data returns view options
    def load(self, filename=None):

        workbook = load_workbook(filename=filename)
        if 'Description' in workbook.sheetnames:
            sheet = workbook['Description']
            description = sheet.cell(column=1, row=1).value
            revision_num = sheet.cell(column=2, row=1).value
            if revision_num is not None:
                self.revision_num = revision_num

        # Read Previously saved data into pandas df - Transactions
        trans_df = pd.read_excel(filename, sheet_name='All Transactions', converters = {'my_str_column': list})
        # trans_df['linked_transactions'] = trans_df['linked_transactions'].apply(lambda x: literal_eval(str(x)))
        trans_df.reset_index(inplace=True)
        
        # Read Previously saved data into pandas df - Conversions
        conversion_df = pd.read_excel(filename, sheet_name='Conversions', converters = {'my_str_column': list})
        conversion_df.reset_index(inplace=True)

        # Read Previously saved data into pandas df - Assets
        asset_df = pd.read_excel(filename, sheet_name='Assets', converters = {'my_str_column': list})

        # Read Previously saved data into pandas df - Links
        links_df = pd.read_excel(filename, sheet_name='Links', converters = {'my_str_column': list})

        # Split Buys and Sells into separate df's
        sell_df = trans_df[(trans_df['trans_type'] == 'sell')].copy()
        buy_df = trans_df[(trans_df['trans_type'] == 'buy')].copy()
        send_df = trans_df[(trans_df['trans_type'] == 'send')].copy()
        receive_df = trans_df[(trans_df['trans_type'] == 'receive')].copy()
        
        send_df.reset_index(inplace=True)
        sell_df.reset_index(inplace=True)
        buy_df.reset_index(inplace=True)
        receive_df.reset_index(inplace=True)
        
        sell_df.sort_values(by='time_stamp', inplace=True)
        buy_df.sort_values(by='time_stamp', inplace=True)
        send_df.sort_values(by='time_stamp', inplace=True)
        receive_df.sort_values(by='time_stamp', inplace=True)

        # Objects >
        sells = []
        buys = []
        sends = []
        receives = []
        conversions = []
        asset_objects = []


        # Load Transactions into Objects
        
        # Load Sells
        for index, row in sell_df.iterrows():
            trans_obj = Sell(symbol=row['symbol'], quantity=row['quantity'], time_stamp=row['time_stamp'], usd_spot=row['usd_spot'], source=row['source'])
            trans_obj.fee = row['fee']
            sells.append(trans_obj)

        # Load Buys
        for index, row in buy_df.iterrows():
            trans_obj = Buy(symbol=row['symbol'], quantity=row['quantity'], time_stamp=row['time_stamp'], usd_spot=row['usd_spot'],  source=row['source'])
            trans_obj.fee = row['fee']
            buys.append(trans_obj)

        # Load Sends
        for index, row in send_df.iterrows():
            # buys.append(Buy(symbol='BTC', quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction']))
            sends.append(Send(symbol=row['symbol'], quantity=row['quantity'], time_stamp=row['time_stamp'], usd_spot=row['usd_spot'],  source=row['source']))

        # Load Receives
        for index, row in receive_df.iterrows():
            # buys.append(Buy(symbol='BTC', quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction']))
            receives.append(Receive(symbol=row['symbol'], quantity=row['quantity'], time_stamp=row['time_stamp'], usd_spot=row['usd_spot'], source=row['source']))
        
        # Load Conversions
        for index, row in conversion_df.iterrows():
            conversions.append(Conversion(
                input_trans_type=row['input_trans_type'],
                output_trans_type=row['output_trans_type'],
                input_symbol=row['symbol'],
                input_quantity=row['quantity'],
                input_time_stamp=row['time_stamp'],
                input_usd_spot=row['usd_spot'],
                input_usd_total=row['usd_total'],
                reason=row['reason'],
                source=row['source']               
                )
            )

        # load Assets
        for index, row in asset_df.iterrows():
            asset_objects.append(Asset(symbol=row['symbol'], hodl=row['hodl']))

        self.asset_objects = asset_objects

        imported_transactions = buys + sells + sends + receives

        # Duplicates check
        transactions = set()
        for trans in imported_transactions:
            transactions.add(trans)

        # Multi-Link Indicator
        for trans in transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()

        self.transactions = list(transactions)
        self.conversions = conversions

        # Re-import Re-Create Links
        for index, row in links_df.iterrows():
            buy = row['buy'].strip("'")
            sell = row['sell'].strip("'")
            quantity = row['quantity']

            buy_obj = None
            sell_obj = None
            
            for trans in self.transactions:

                if trans.name == sell:
                    # print(f'Sell Found {trans.name}')
                    if trans.trans_type == 'sell':
                        sell_obj = trans

                elif trans.name == buy:                
                    # print(f'Buy Found {trans.name}')
                    if trans.trans_type == 'buy':
                        buy_obj = trans

                if buy_obj and sell_obj:
                    # print("Buy and Sell Found Breaking\n")
                    break
            
            if sell_obj and buy_obj:
                
                # print(f" quantity of link on load {quantity}")
                sell_obj.link_transaction(buy_obj, link_quantity=quantity)


        return list(transactions)


    def filter(self, symbols, options):

        trans_in_view = set()
        
        for trans in self.transactions:

            # if symbol in view
            if trans.symbol in symbols:
            
                # if has_link in options
                if 'has_link' in options:
                    if len(trans.links) > 0:
                        trans_in_view.add(trans)
                
                if 'needs_link' in options and trans.trans_type == 'sell':
                    if trans.unlinked_quantity > 0.0:
                        trans_in_view.add(trans)

                if 'no_link' in options:
                    if len(trans.links) == 0:
                        trans_in_view.add(trans)
                        

        return list(trans_in_view)


    def save(self, description=None):
        save_as_filename = os.path.join(basedir, "saves", f"saved_{strftime('Y%Y-M%m-D%d_H%H-M%M-S%S')}.xlsx")
        
        for trans in self.transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()
        
        trans_df = pd.DataFrame([vars(s) for s in self.transactions])
        conversion_df = pd.DataFrame([vars(s) for s in self.conversions])
        asset_df = pd.DataFrame([vars(s) for s in self.asset_objects])

        # for link in self.links:
        #     print(f"Link Quantity before save {link.quantity}")


        # links_df = pd.DataFrame([vars(s) for s in self.links])

        # for link in self.links:
            # print(f"\nQuantity of link on Save {link.quantity} \n   buy quantity {link.buy.quantity} unlinked {link.buy.unlinked_quantity} \n   sell quantity {link.sell.quantity} unlinked {link.sell.unlinked_quantity}")

        
        with pd.ExcelWriter(save_as_filename,  engine = 'xlsxwriter') as writer:
            # links_df.to_excel(writer, sheet_name="Links")
            # trans_df.to_excel(writer, sheet_name="All Transactions")
            conversion_df.to_excel(writer, sheet_name="Conversions")
            asset_df.to_excel(writer, sheet_name="Assets")
            

        # Saving workbook description
        workbook = load_workbook(filename=save_as_filename)
        sheet = workbook.create_sheet('Description')
        sheet.cell(row=1, column=1, value=description)
        revision_num = self.revision_num
        if revision_num is None:
            revision_num = 0
        sheet.cell(row=1, column=2, value=revision_num + 1)


        # Trying creating links outside of pd
        sheet = workbook.create_sheet('Links')
        sheet.cell(row=1, column=1, value='id')
        sheet.cell(row=1, column=2, value='quantity')
        sheet.cell(row=1, column=3, value='buy')
        sheet.cell(row=1, column=4, value='sell')
        sheet.cell(row=1, column=5, value='symbol')

        index = 2
        for l in self.links:
            sheet.cell(row=index, column=1, value=l.symbol)
            sheet.cell(row=index, column=2, value=str(l.quantity))
            sheet.cell(row=index, column=3, value=str(l.buy))
            sheet.cell(row=index, column=4, value=str(l.sell))
            sheet.cell(row=index, column=5, value=l.symbol)
            index += 1


        # Trying creating transactions outside of pd ( no changes noticed reverting)
        sheet = workbook.create_sheet('All Transactions')
        sheet.cell(row=1, column=1, value='symbol')
        sheet.cell(row=1, column=2, value='quantity')
        sheet.cell(row=1, column=3, value='time_stamp')
        sheet.cell(row=1, column=4, value='usd_spot')
        sheet.cell(row=1, column=5, value='source')
        sheet.cell(row=1, column=6, value='trans_type')
        sheet.cell(row=1, column=7, value='fee')


        index = 2
        for t in self.transactions:
            sheet.cell(row=index, column=1, value=t.symbol)
            sheet.cell(row=index, column=2, value=str(t.quantity))
            sheet.cell(row=index, column=3, value=t.time_stamp)
            sheet.cell(row=index, column=4, value=t.usd_spot)
            sheet.cell(row=index, column=5, value=t.source)
            sheet.cell(row=index, column=6, value=t.trans_type)
            sheet.cell(row=index, column=7, value=t.fee)
            index += 1


        workbook.save(save_as_filename)
        workbook.close()
        print(f"{description} Saving to {save_as_filename}")

        self.saves = self.load_saves()
        self.view = save_as_filename
        
        return save_as_filename


    def delete(self, filename):
        os.rename(filename, f"{filename}.bak")


    def export_to_excel(self, asset=None, date_range=None, by_year=True):

        # Idea to programatically create Excel Links, Fancy ;-)
        # =HYPERLINK("[Export_Y2021-M03-D06_H19-M34.xlsx]Links!A20","Display Text")
        
        save_as_filename = os.path.join(basedir, "Exports", f"Export_{strftime('Y%Y-M%m-D%d_H%H-M%M')}.xlsx")
        
        # Template to use
        workbook = load_workbook(filename= os.path.join(basedir, 'Gainz_Export_Template-DO_NOT_MODIFY.xlsx'))
        c_sheet = workbook['Conversions']
        l_sheet = workbook['Gains']
        a_sheet = workbook['All Transactions']
        s_sheet = workbook['Stats']
        t8949_sheet = workbook['8949']
        sales_sheet = workbook['Sales']

        
        # Get Years
        years = set()
        for link in self.links:
            years.add(link.sell.time_stamp.year)

        # Sales
        for year in years:
            print(f'exporting sales for {year}')


            sheetname = f'{year} Sales'
            ws = workbook.copy_worksheet(sales_sheet)
            ws.title = sheetname

            row = 2
            
            for trans in self.transactions:
                
                description = None
                acquired = None
                sold_date = None
                proceeds = None 
                cost_basis = 0
                source = None
                gain_loss = 0


                if trans.trans_type != "sell":
                    continue

                if trans.time_stamp.year != year:
                    continue
                

                description = f"{trans.quantity} of {trans.symbol}"
                
                ws[f"A{row}"] = description

                if len(trans.links) == 0:
                    continue
                elif len(trans.links) > 1:
                    acquired = "Multiple Dates"
                    all_short = True
                    all_long = True
                    
                    for link in trans.links:


                        gain_loss += link.profit_loss
                        if link.hodl_duration.days < 365:
                            all_long = False
                        else:
                            all_short = False
                    
                    if all_long is False and all_short is False:
                        acquired += " Long and Short"

                    elif all_long is True:
                        acquired += " All Long"
                    
                    elif all_short is True:
                        acquired += " All Short"

                        
                else:
                    gain_loss = trans.links[0].profit_loss
                    acquired = trans.links[0].buy.time_stamp

                ws[f"B{row}"] = acquired

                sold_date = trans.time_stamp

                ws[f"C{row}"] = sold_date

                proceeds = trans.usd_total - trans.fee

                ws[f"D{row}"] = proceeds
                ws[f"D{row}"].number_format = '"$"#,##0.00_-'

                for link in trans.links:
                    cost_basis += link.cost_basis + link.buy.fee

                ws[f"E{row}"] = cost_basis
                ws[f"E{row}"].number_format = '"$"#,##0.00_-'

                gain_loss = proceeds - cost_basis

                ws[f"F{row}"] = gain_loss
                ws[f"F{row}"].number_format = '"$"#,##0.00_-'

                source = trans.source
                ws[f"G{row}"] = source

                row += 1


        # 8949 Short
        for year in years:
            
            sheetname = f'{year} 8949 Short'
            ws = workbook.copy_worksheet(t8949_sheet)
            ws.title = sheetname
            
            row = 2
            for link in self.links:

                if link.sell.time_stamp.year != year:
                    continue

                if abs(link.profit_loss) <= 1:
                    continue
                
                if link.hodl_duration.days > 365:
                    continue

                ws[f"A{row}"] = f"Crypto {link.symbol}"
                ws[f"B{row}"] = link.buy.time_stamp
                ws[f"C{row}"] = link.sell.time_stamp
                ws[f"D{row}"] = link.link_sell_price
                ws[f"D{row}"].number_format = '"$"#,##0.00_-'
                ws[f"E{row}"] = link.link_buy_price
                ws[f"E{row}"].number_format = '"$"#,##0.00_-'
                ws[f"H{row}"] = link.profit_loss
                ws[f"H{row}"].number_format = '"$"#,##0.00_-'
                ws[f"I{row}"] = link.sell.source

                row += 1

            if row == 2:
                workbook.remove(ws)

            else:
                row += 2

                ws[f"C{row}"] = "Totals"

                ws[f"D{row}"] = f"=SUM(D2:D{row -2})"
                ws[f"D{row}"].number_format = '"$"#,##0.00_-'
                ws[f"E{row}"] = f"=SUM(E2:E{row -2})"
                ws[f"E{row}"].number_format = '"$"#,##0.00_-'
                ws[f"H{row}"] = f"=SUM(H2:H{row -2})"
                ws[f"H{row}"].number_format = '"$"#,##0.00_-'


        # 8949 Long
        years = set()
        for link in self.links:

            years.add(link.sell.time_stamp.year)

        for year in years:
            
            sheetname = f'{year} 8949 Long'
            ws = workbook.copy_worksheet(t8949_sheet)
            ws.title = sheetname
            
            row = 2
            for link in self.links:

                if link.sell.time_stamp.year != year:
                    continue

                if abs(link.profit_loss) <= 1:
                    continue
                
                if link.hodl_duration.days <= 365:
                    continue

                ws[f"A{row}"] = f"Crypto {link.symbol}"
                ws[f"B{row}"] = link.buy.time_stamp
                ws[f"C{row}"] = link.sell.time_stamp
                ws[f"D{row}"] = link.link_sell_price
                ws[f"D{row}"].number_format = '"$"#,##0.00_-'
                ws[f"E{row}"] = link.link_buy_price
                ws[f"E{row}"].number_format = '"$"#,##0.00_-'
                ws[f"H{row}"] = link.profit_loss
                ws[f"H{row}"].number_format = '"$"#,##0.00_-'
                ws[f"I{row}"] = link.sell.source

                row += 1

            if row == 2:
                workbook.remove(ws)

            else:
                row += 2

                ws[f"C{row}"] = "Totals"

                ws[f"D{row}"] = f"=SUM(D2:D{row -2})"
                ws[f"D{row}"].number_format = '"$"#,##0.00_-'
                ws[f"E{row}"] = f"=SUM(E2:E{row -2})"
                ws[f"E{row}"].number_format = '"$"#,##0.00_-'
                ws[f"H{row}"] = f"=SUM(H2:H{row -2})"
                ws[f"H{row}"].number_format = '"$"#,##0.00_-'


        for asset in self.assets:
            
            # Conversions sheet
            sheetname = f'{asset} Conversions'
            conversions_sheet = workbook.copy_worksheet(c_sheet)
            conversions_sheet.title = sheetname

            column_names = []
            for cell in conversions_sheet[3]:
                column_names.append(cell.value)
            
            in_trans_type_index = column_names.index("In Transaction Type") + 1
            out_trans_type_index = column_names.index("Out Transaction Type") + 1
            symbol_index = column_names.index("Symbol") + 1
            time_stamp_index = column_names.index("Time Stamp") + 1
            quantity_index = column_names.index("Quantity") + 1
            usd_spot_index = column_names.index("USD Spot") + 1
            usd_total_index = column_names.index("USD Total") + 1
            reason_index = column_names.index("Reason") + 1

            row = 4
            for conversion in self.conversions:
                
                if conversion.symbol != asset:
                    continue

                conversions_sheet.cell(row=row, column=in_trans_type_index, value=conversion.input_trans_type)
                conversions_sheet.cell(row=row, column=out_trans_type_index, value=conversion.output_trans_type)
                conversions_sheet.cell(row=row, column=symbol_index, value=conversion.symbol)
                conversions_sheet.cell(row=row, column=time_stamp_index, value=conversion.time_stamp)
                conversions_sheet.cell(row=row, column=quantity_index, value=conversion.quantity)
                
                conversions_sheet.cell(row=row, column=usd_spot_index, value=conversion.usd_spot)
                conversions_sheet.cell(row=row, column=usd_spot_index).number_format = '"$"#,##0.00_-'
                
                conversions_sheet.cell(row=row, column=usd_total_index, value=conversion.usd_total)
                conversions_sheet.cell(row=row, column=usd_total_index).number_format = '"$"#,##0.00_-'
                
                conversions_sheet.cell(row=row, column=reason_index, value=conversion.reason)

                row += 1

            if row == 4:
                workbook.remove(conversions_sheet)


            # Gainz Sheet
            column_names = []
            for cell in l_sheet[1]:
                column_names.append(cell.value)

            sell_date_index = column_names.index("Sell Date") + 1
            sell_id_index = column_names.index("Sell ID") + 1
            sell_quantity_index = column_names.index("Sell Quantity") + 1
            sell_unlinked_index = column_names.index("Sell Unlinked") + 1
            sell_usd_total_index = column_names.index("Sell USD Total") + 1
            sell_usd_spot_index = column_names.index("Sell Spot USD") + 1
            sell_multi_link_index = column_names.index("Sell Multi-Link") + 1

            buy_link_usd_index = column_names.index("Link Buy in USD") + 1
            link_id_index = column_names.index("Link ID") + 1
            link_symbol_index = column_names.index("Link Asset") + 1
            link_quantity_index = column_names.index("Link Quantity") + 1
            link_profit_loss_index = column_names.index("Link Profit Loss") + 1
            sell_link_usd_index = column_names.index("Link Sell in USD") + 1
            date_acquired_index = column_names.index("Date Acquired") + 1

            buy_multi_link_index = column_names.index("Buy Multi-Link") + 1
            buy_date_index = column_names.index("Buy Date") + 1
            buy_id_index = column_names.index("Buy ID") + 1
            buy_quantity_index = column_names.index("Buy Quantity") + 1
            buy_unlinked_index = column_names.index("Buy Unlinked") + 1
            buy_usd_total_index = column_names.index("Buy USD Total") + 1
            buy_usd_spot_index = column_names.index("Buy Spot USD") + 1

            years = set()
            for link in self.links:
                if link.symbol != asset:
                    continue

                years.add(link.sell.time_stamp.year)

            for year in years:
                
                sheetname = f'{year} {asset} Gains'
                links_sheet = workbook.copy_worksheet(l_sheet)
                links_sheet.title = sheetname
                        
                row = 2
                profit_loss_total = 0.0
                for link in self.links:
                    
                    if link.symbol != asset:
                        continue
                        
                    if link.sell.time_stamp.year != year:
                        continue

                    if link.quantity <= 0.00000001:
                        continue

                    profit_loss_total += float(link.profit_loss)
                    
                    links_sheet.cell(row=row, column=link_symbol_index, value=link.sell.symbol)
                    links_sheet.cell(row=row, column=link_id_index, value=link.id)
                    links_sheet.cell(row=row, column=buy_id_index, value=link.buy.id)
                    links_sheet.cell(row=row, column=sell_id_index, value=link.sell.id)
                    links_sheet.cell(row=row, column=buy_date_index, value=link.buy.time_stamp)
                    links_sheet.cell(row=row, column=buy_quantity_index, value=link.buy.quantity)
                    links_sheet.cell(row=row, column=buy_unlinked_index, value=link.buy.unlinked_quantity)
                    
                    links_sheet.cell(row=row, column=buy_usd_spot_index, value=link.buy.usd_spot)
                    links_sheet.cell(row=row, column=buy_usd_spot_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=buy_usd_total_index, value=link.buy.usd_total)
                    links_sheet.cell(row=row, column=buy_usd_total_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=buy_link_usd_index, value=link.link_buy_price)
                    links_sheet.cell(row=row, column=buy_link_usd_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=link_quantity_index, value=link.quantity)
                    
                    links_sheet.cell(row=row, column=link_profit_loss_index, value=link.profit_loss)
                    links_sheet.cell(row=row, column=link_profit_loss_index).number_format = '"$"#,##0.00_);[Red]("$"#,##0.00)'

                    links_sheet.cell(row=row, column=sell_link_usd_index, value=link.link_sell_price)
                    links_sheet.cell(row=row, column=sell_link_usd_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=sell_date_index, value=link.sell.time_stamp)
                    links_sheet.cell(row=row, column=sell_quantity_index, value=link.sell.quantity)
                    links_sheet.cell(row=row, column=sell_unlinked_index, value=link.sell.unlinked_quantity)

                    links_sheet.cell(row=row, column=sell_usd_spot_index, value=link.sell.usd_spot)
                    links_sheet.cell(row=row, column=sell_usd_spot_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=sell_usd_total_index, value=link.sell.usd_total)
                    links_sheet.cell(row=row, column=sell_usd_total_index).number_format = '"$"#,##0.00_-'
                    
                    links_sheet.cell(row=row, column=sell_multi_link_index, value=link.sell.multi_link)
                    links_sheet.cell(row=row, column=buy_multi_link_index, value=link.buy.multi_link)
                    
                    row += 1

                for trans in self.transactions:
                    
                    if trans.symbol != asset:
                        continue

                    if trans.trans_type != 'sell':
                        continue

                    if trans.time_stamp.year != year:
                        continue

                    if trans.unlinked_quantity <= 0.00000001:
                        continue

                    profit_loss_total += float(trans.unlinked_quantity * trans.usd_spot)

                    links_sheet.cell(row=row, column=link_symbol_index, value="N/A")
                    links_sheet.cell(row=row, column=link_id_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_id_index, value="N/A")
                    links_sheet.cell(row=row, column=sell_id_index, value=trans.id)
                    links_sheet.cell(row=row, column=buy_date_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_quantity_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_unlinked_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_usd_spot_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_usd_total_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_link_usd_index, value="N/A")
                    links_sheet.cell(row=row, column=link_quantity_index, value=trans.unlinked_quantity)

                    links_sheet.cell(row=row, column=link_profit_loss_index, value=(trans.unlinked_quantity * trans.usd_spot))
                    links_sheet.cell(row=row, column=link_profit_loss_index).number_format = '"$"#,##0.00_);[Red]("$"#,##0.00)'
                    
                    links_sheet.cell(row=row, column=sell_link_usd_index, value=trans.usd_total)
                    links_sheet.cell(row=row, column=sell_link_usd_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=sell_date_index, value=trans.time_stamp)
                    links_sheet.cell(row=row, column=sell_quantity_index, value=trans.quantity)
                    links_sheet.cell(row=row, column=sell_unlinked_index, value=trans.unlinked_quantity)
                    links_sheet.cell(row=row, column=sell_usd_spot_index, value=trans.usd_spot)
                    links_sheet.cell(row=row, column=sell_usd_spot_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=sell_usd_total_index, value=trans.usd_total)
                    links_sheet.cell(row=row, column=sell_usd_total_index).number_format = '"$"#,##0.00_-'

                    links_sheet.cell(row=row, column=sell_multi_link_index, value="N/A")
                    links_sheet.cell(row=row, column=buy_multi_link_index, value="N/A")

                    row += 1
                    

                row += 2

                links_sheet.cell(row=row, column=link_profit_loss_index, value="Profit/Loss Total: ${:,.2f}".format(profit_loss_total)) 

                if row == 4:
                    workbook.remove(links_sheet)

            # All Transactions sheet
            sheetname = f'{asset} Transactions'
            all_trans_sheet = workbook.copy_worksheet(a_sheet)
            all_trans_sheet.title = sheetname
            
            column_names = []
            for cell in all_trans_sheet[1]:
                column_names.append(cell.value)

            id_index = column_names.index("Transaction ID") + 1
            symbol_index = column_names.index("Symbol") + 1
            trans_type_index = column_names.index("Transaction Type") + 1
            time_stamp_index = column_names.index("Time Stamp") + 1 
            quantity_index = column_names.index("Quantity") + 1
            links_index = column_names.index("Links") + 1
            unlinked_index = column_names.index("Unlinked") + 1
            usd_spot_index = column_names.index("USD Spot") + 1
            usd_total_index = column_names.index("USD Total") + 1
            source_index = column_names.index("Source") + 1
            
            row = 2
            for trans in self.transactions:

                if trans.symbol != asset:
                    continue

                all_trans_sheet.cell(row=row, column=id_index, value=trans.id)
                all_trans_sheet.cell(row=row, column=symbol_index, value=trans.symbol)
                all_trans_sheet.cell(row=row, column=trans_type_index, value=trans.trans_type)
                all_trans_sheet.cell(row=row, column=time_stamp_index, value=trans.time_stamp)
                all_trans_sheet.cell(row=row, column=quantity_index, value=trans.quantity)
                all_trans_sheet.cell(row=row, column=unlinked_index, value=trans.unlinked_quantity)

                all_trans_sheet.cell(row=row, column=usd_spot_index, value=trans.usd_spot)
                all_trans_sheet.cell(row=row, column=usd_spot_index).number_format = '"$"#,##0.00_-'

                all_trans_sheet.cell(row=row, column=usd_total_index, value=trans.usd_total)
                all_trans_sheet.cell(row=row, column=usd_total_index).number_format = '"$"#,##0.00_-'

                all_trans_sheet.cell(row=row, column=source_index, value=trans.source)

                if len(trans.links) > 0:
                    all_trans_sheet.cell(row=row, column=links_index, value=str(trans.links))

                row += 1

            if row == 2:
                workbook.remove(all_trans_sheet)


            # Links Sheet
            sheetname = f'{asset} Stats'
            asset_stats_sheet = workbook.copy_worksheet(s_sheet)
            asset_stats_sheet.title = sheetname


            date_range = {
                'start_date': '',
                'end_date': ''
            }

            date_range = get_transactions_date_range(self, date_range)

            # get stats table data 
            stats_table_data = get_stats_table_data_range(self, date_range)

            # get stats for selected asset
            asset_stats = None
            for a in stats_table_data:
                if a['symbol'] == asset:
                    asset_stats = a
                    break
                
           
            # print(asset_stats)

            # Create detailed stats table data
            detailed_stats = [
                ["Quantity Purchased", asset_stats['total_purchased_quantity']],
                ["Number of Buys", asset_stats["num_buys"]],
                ["Number of Sells", asset_stats["num_sells"]],
                ["Number of Links", asset_stats["num_links"]],
                ["Average Buy Price", asset_stats["average_buy_price"]],
                ["Average Sell Price", asset_stats["average_sell_price"]],
                ["Quantity Sold", asset_stats['total_sold_quantity']],
                ["Quantity Sold Unlinked", asset_stats['total_sold_unlinked_quantity']],
                ["Quantity Purchased Unlinked", asset_stats['total_purchased_unlinked_quantity']],
                ["Quantity Purchased in USD", asset_stats['total_purchased_usd']],
                ["Quantity Sold in USD", asset_stats['total_sold_usd']],
                ["Profit / Loss in USD* (Valid when Quantity Sold Unlinked is 0)", asset_stats['profit_loss_total']],
            ]

            row = 2
            for i in detailed_stats:
                asset_stats_sheet.cell(row=row, column=1, value=i[0])
                asset_stats_sheet.cell(row=row, column=1).number_format = '"$"#,##0.00_-'
                asset_stats_sheet.cell(row=row, column=2, value=i[1])
                asset_stats_sheet.cell(row=row, column=2).number_format = '"$"#,##0.00_-'
                
                row += 1

        
        workbook.remove(a_sheet)
        workbook.remove(c_sheet)
        workbook.remove(l_sheet)
        workbook.remove(s_sheet)
        workbook.remove(t8949_sheet)
        workbook.remove(sales_sheet)
            
            
        workbook.save(save_as_filename)
        print(f"Saving to {save_as_filename}")

        return save_as_filename


        
    def import_transaction(self, type, timestamp, quantity):

        if type.lower() == 'buy':
            trans = Buy(trans_type=type, time_stamp=timestamp, quantity=quantity, symbol='BTC', source='Gainz App')
        elif type.lower() == 'sell':
            trans = Sell(trans_type=type, time_stamp=timestamp, quantity=quantity, symbol='BTC', source='Gainz App')
        
        self.transactions.append(trans)
        print(len(self.transactions))

        return trans


    def import_transactions(self, contents, filename):

        # Objects 
        sells = []
        buys = []
        sends = []
        receives = []
        assets = []

        
        if type(contents) is str:

            # This isn't used
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            try:
                if 'csv' in filename:
                    if 'cash_app' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                        
                    elif 'coinbasetransactions' in filename.lower() or 'coinbase-transactions' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip', skip_blank_lines=False, header=7)
                    elif 'coinbase' in filename.lower() and 'pro' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                    elif 'kraken' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                    else:
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                elif 'xls' in filename or 'xlsx' in filename:
                    # Assume that the user uploaded an excel file
                    trans_df = pd.read_excel(io.BytesIO(decoded))
                
            except Exception as e:
                print(e)
        else:
            try:
                if 'csv' in filename:
                    if 'cash_app' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                    elif 'coinbasetransactions' in filename.lower() or 'coinbase-transactions' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip', skip_blank_lines=False, header=7)

                    elif 'coinbase' in filename.lower() and 'pro' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                    elif 'kraken' in filename.lower():
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
                    else:
                        trans_df = pd.read_csv(contents, on_bad_lines='skip')
               
                elif 'xls' in filename or 'xlsx' in filename:
                    # Assume that the user uploaded an excel file
                    trans_df = pd.read_excel(contents)
                else:
                    trans_df = pd.read_csv(contents, on_bad_lines='skip')
            
            except Exception as e:
                print(e)

        # print(f"Base Dir in import transactions {basedir}")
        # pathlib.Path(os.path.join(basedir, "saves")).mkdir(parents=True, exist_ok=True) 

        save_as_filename = os.path.join(basedir, "saves", f"saved_{strftime('Y%Y-M%m-D%d_H%H-M%M-S%S')}.xlsx")

        # Import from CashApp csv
        if 'cash_app' in filename.lower():

            # print("Date Found in columns")
            trans_df.rename(columns={'Date': 'Timestamp', 'Asset Type': 'Asset', 'Asset Amount': 'Quantity Transacted', 'Asset Price': 'Spot Price at Transaction'}, inplace=True)
            
            # Only keep columns needed.
            # trans_df = trans_df[['Fee', 'Transaction Type', 'Timestamp', 'Asset', "Quantity Transacted", "Spot Price at Transaction" ]]
            
            trans_df['Timestamp'] = trans_df['Timestamp'].apply(dateutil.parser.parse, tzinfos=whois_timezone_info)
            trans_df['Timestamp'] = pd.to_datetime(trans_df['Timestamp'], infer_datetime_format=True, utc=True) 
            trans_df['Timestamp'] = trans_df['Timestamp'].dt.tz_localize(None)

            trans_df['Spot Price at Transaction'] = trans_df['Spot Price at Transaction'].replace('[\$,]', '', regex=True).astype(float)
            trans_df['Source'] = filename

            sell_df = trans_df[trans_df['Transaction Type'] == 'Bitcoin Sale'].copy()
            buy_df = trans_df[trans_df['Transaction Type'] == 'Bitcoin Buy'].copy()
            send_df = trans_df[trans_df['Transaction Type'] == 'Bitcoin Withdrawal'].copy()
            receive_df = trans_df[trans_df['Transaction Type'] == 'Bitcoin Deposit'].copy()

            # Sells
            for index, row in sell_df.iterrows():
                trans_obj = Sell(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                trans_obj.fee = row['Fee'][2:]
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    sells.append(trans_obj)

            # Buys
            for index, row in buy_df.iterrows():

                trans_obj = Buy(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                duplicate_found = False
                trans_obj.fee = row['Fee'][2:]
                trans_obj.fee = trans_obj.fee
                
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    buys.append(trans_obj)

            # Sends
            for index, row in send_df.iterrows():
                trans_obj = Send(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    sends.append(trans_obj)

            # Receives
            for index, row in receive_df.iterrows():
                trans_obj = Receive(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    receives.append(trans_obj)


        #import from coinbase csv
        elif 'coinbase-transactions' in filename.lower() or 'coinbasetransactions' in filename.lower():

            print(trans_df.columns)

            trans_df.rename(columns={'Fees and/or Spread': 'Fee'}, inplace=True)

            
            trans_df['Timestamp'] = pd.to_datetime(trans_df['Timestamp']) 
            trans_df['Timestamp'] = trans_df['Timestamp'].dt.tz_localize(None)
            trans_df['Source'] = filename

            sell_df = trans_df[trans_df['Transaction Type'] == 'Sell'].copy()
            buy_df = trans_df[trans_df['Transaction Type'] == 'Buy'].copy()
            send_df = trans_df[trans_df['Transaction Type'] == 'Send'].copy()
            receive_df = trans_df[trans_df['Transaction Type'] == 'Receive'].copy()
            convert_df = trans_df[trans_df['Transaction Type'] == 'Convert'].copy()

            # Sells
            for index, row in sell_df.iterrows():
                duplicate_found = False
                
                trans_obj = Sell(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                trans_obj.fee = row['Fee']

                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    sells.append(trans_obj)

            # Buys
            for index, row in buy_df.iterrows():
                duplicate_found = False
                
                trans_obj = Buy(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                trans_obj.fee = row['Fee']
                
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    buys.append(trans_obj)

            # Sends
            for index, row in send_df.iterrows():
                trans_obj = Send(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    sends.append(trans_obj)

            # Receives
            for index, row in receive_df.iterrows():
                trans_obj = Receive(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=row['Source'])
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    receives.append(trans_obj)


            # Converts
            convert_df.reset_index(inplace=True)
            for index, row in convert_df.iterrows():

                symbol=row['Asset']
                quantity=row['Quantity Transacted']
                time_stamp=row['Timestamp']
                usd_spot=row['Spot Price at Transaction']
                source=row['Source']

                sells.append(Sell(symbol=row['Asset'], quantity=row['Quantity Transacted'], time_stamp=row['Timestamp'], usd_spot=row['Spot Price at Transaction'], source=f"{row['Source']} - Convert Sell"))

                usd_total = row['Total (inclusive of fees and/or spread)']

                notes = row['Notes']

                buy_quantity = float(notes.split()[4])
                buy_asset = notes.split()[5]

                buy_usd_spot = usd_total / buy_quantity

                buys.append(Buy(symbol=buy_asset, quantity=buy_quantity, time_stamp=row['Timestamp'], usd_spot=buy_usd_spot, source=f"{row['Source']} - Convert Buy" ))
        
        # Import from coinbase pro fills
        elif 'coinbase' in filename.lower() and 'pro' in filename.lower():
            
            print("Starting Coinbase pro Import")
            
            threads = list()
            trans_df.sort_values(by=['trade id'], inplace=True)
            trans_df.reset_index(inplace=True)
            
            for index,row in trans_df.iterrows():
                
                quantity = None
                amount_in_usd = None
                symbol = None
                fee = None
                timestamp = None
                buy = None
                sell = None
                
                pair_one_is_crypto = False
                pair_two_is_crypto = False

                trade_id = str(row['trade id'])

                timestamp = dateutil.parser.parse(row['time'])
                timestamp = timestamp.replace(tzinfo=None)
                
                symbol = row['amount/balance unit']
                
                # Received Crypto
                if row['amount/balance unit'] != 'USD' and row['type'] == 'deposit':
                    trans_obj = Receive(symbol=symbol, quantity=abs(row['amount']), time_stamp=timestamp, usd_spot=0.0, source=filename)
                    receives.append(trans_obj)
                    continue

                # Sent Crypto
                elif row['amount/balance unit'] != 'USD' and row['type'] == 'withdrawal':
                    trans_obj = Receive(symbol=symbol, quantity=abs(row['amount']), time_stamp=timestamp, usd_spot=0.0, source=filename)
                    sends.append(trans_obj)
                    continue
            
                # Row is buy with USD
                elif row['amount/balance unit'] == 'USD' and row['type'] == 'match' and float(row['amount']) < 0:
                    amount_in_usd = row['amount']


                # Row is Sell for USD
                elif row['amount/balance unit'] == 'USD' and row['type'] == 'match' and float(row['amount']) > 0:
                    amount_in_usd = row['amount']

                # Row is crypto sold 
                elif row['amount/balance unit'] != 'USD' and row['type'] == 'match' and row['amount'] < 0:
                    symbol = row['amount/balance unit']
                    quantity = row['amount']
                    pair_one_is_crypto = True
                    pair_one_symbol = symbol
                    pair_one_quantity = quantity

                
                # Row is Crypto Bought
                elif row['amount/balance unit'] != 'USD' and row['type'] == 'match' and row['amount'] > 0:
                    symbol = row['amount/balance unit']
                    quantity = row['amount']
                    pair_one_is_crypto = True
                    pair_one_symbol = symbol
                    pair_one_quantity = quantity

                i = 1
                while (index + i <= trans_df.index[-1]) and str(trans_df.loc[index + i]['trade id']) == trade_id:
                                        
                    # Row is buy with USD
                    if trans_df.loc[index + i]['amount/balance unit'] == 'USD' and trans_df.loc[index + i]['type'] == 'match' and trans_df.loc[index + i]['amount'] < 0:
                        amount_in_usd =  trans_df.loc[index + i]['amount']

                        
                    # Row is Sell for USD
                    elif trans_df.loc[index + i]['amount/balance unit'] == 'USD' and trans_df.loc[index + i]['type'] == 'match' and trans_df.loc[index + i]['amount'] > 0:
                        amount_in_usd =  trans_df.loc[index + i]['amount']

                    
                    # Row is crypto sold
                    elif trans_df.loc[index + i]['amount/balance unit'] != 'USD' and  trans_df.loc[index + i]['type'] == 'match' and  trans_df.loc[index + i]['amount'] < 0:
                        symbol = trans_df.loc[index + i]['amount/balance unit']
                        quantity = trans_df.loc[index + i]['amount']
                        
                        pair_two_is_crypto = True
                        pair_two_symbol = symbol
                        pair_two_quantity = quantity


                    # Row is Crypto Bought
                    elif trans_df.loc[index + i]['amount/balance unit'] != 'USD' and  trans_df.loc[index + i]['type'] == 'match' and  trans_df.loc[index + i]['amount'] > 0:
                        symbol = trans_df.loc[index + i]['amount/balance unit']
                        quantity = trans_df.loc[index + i]['amount']
                        
                        pair_two_is_crypto = True
                        pair_two_symbol = symbol
                        pair_two_quantity = quantity

                    i += 1
                    if quantity is not None and symbol is not None and amount_in_usd is not None:

                        # This is a Conversion
                        if pair_one_is_crypto is True and pair_two_is_crypto is True:
                            if pair_one_quantity < 0:
                                print(f"Sold {abs(pair_one_quantity)} {pair_one_symbol} for {abs(pair_two_quantity)} {pair_two_symbol} ")
                            else:
                                print(f"Sold {abs(pair_two_quantity)} {pair_two_symbol} for {abs(pair_one_quantity)} {pair_one_symbol} ")
                            
                        else:
                            # print(f"Found a buy or Sell")
                            time_stamp = dateutil.parser.parse(row['time'])
                            
                            if amount_in_usd > 0:
                                # print(f"Found a {symbol} Sell")
                                sell = Sell(symbol=symbol, quantity=abs(quantity), time_stamp=time_stamp, usd_spot=0.0, source=filename)
                                sells.append(sell)
                                
                            else:
                                # print(f"Found a {symbol} Buy")
                                buy = Buy(symbol=symbol, quantity=abs(quantity), time_stamp=time_stamp, usd_spot=0.0, source=filename)
                                buys.append(buy)
                        
                        break
            
            # Get price from coinbase API
            for trans in sells + buys + receives + sends:
                t = threading.Thread(target=fetch_crypto_price, args=(trans,))
                threads.append(t)
            
            k = 1
            for t in threads:
                time.sleep(.2)
                print(f"Getting usd spot from Coinbase API at max rate for transaction {k} of {len(threads)}")
                t.start()
                k += 1
            
            i = 1
            for t in threads:
                t.join()

            for t in buys + sells:
                t.time_stamp = t.time_stamp.replace(tzinfo=None)

        # Import From Kraken
        elif 'kraken' in filename.lower():
            trans_df['Timestamp'] = pd.to_datetime(trans_df['time']) 
            trans_df['Source'] = filename

            sell_df = trans_df[trans_df['type'] == 'sell'].copy()
            buy_df = trans_df[trans_df['type'] == 'buy'].copy()

            # Sells
            for index, row in sell_df.iterrows():

                kraken_symbol = row['pair']
                first_symbol = kraken_symbol[:-4]
                second_symbol = kraken_symbol[-4:]
                if first_symbol.startswith('X'):
                    symbol = first_symbol[1:]
                    if symbol == 'XBT':
                        symbol = 'BTC'
                
                elif first_symbol.startswith('Z'):
                    currency = first_symbol[1:]

                if second_symbol.startswith('Z'):
                    currency = second_symbol[1:]
                
                elif second_symbol.startswith('X'):
                    symbol = first_symbol[1:]
                    if symbol == 'XBT':
                        symbol = 'BTC'


                trans_obj = Sell(symbol=symbol, quantity=row['vol'], time_stamp=row['Timestamp'], usd_spot=row['price'], source=row['Source'])
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    sells.append(trans_obj)

            # Buys
            for index, row in buy_df.iterrows():
                
                # Get Symbols
                kraken_symbol = row['pair']
                first_symbol = kraken_symbol[:-4]
                second_symbol = kraken_symbol[-4:]
                
                # print(first_symbol, ' ', second_symbol)
                if first_symbol.startswith('X'):
                    symbol = first_symbol[1:]
                    if symbol == 'XBT':
                        symbol = 'BTC'
                elif first_symbol.startswith('Z'):
                    currency = first_symbol[1:]

                if second_symbol.startswith('Z'):
                    currency = second_symbol[1:]
                
                elif second_symbol.startswith('X'):
                    symbol = first_symbol[1:]
                    if symbol == 'XBT':
                        symbol = 'BTC'
                
                
                trans_obj = Buy(symbol=symbol, quantity=row['vol'], time_stamp=row['Timestamp'], usd_spot=row['price'], source=row['Source'])
                
                duplicate_found = False
                for trans in self.conversions:
                    if (
                        trans.input_trans_type == trans_obj.trans_type
                        and trans.symbol == trans_obj.symbol
                        and trans.quantity == trans_obj.quantity
                        and trans.usd_spot == trans_obj.usd_spot
                        and trans.usd_total == math.floor(trans_obj.usd_total * 10 ** 10) / 10 ** 10 
                    ):

                        duplicate_found = True

                if duplicate_found is False:
                    buys.append(trans_obj)


        # Dedup and merge Transactions
        if self.transactions:
            starting = len(self.transactions)
            
            imported_transactions =  buys + sells + sends + receives
            
            deduped_transactions = set()

            for trans in self.transactions:
                deduped_transactions.add(trans)

            for trans in imported_transactions:
                deduped_transactions.add(trans)

            self.transactions = list(deduped_transactions)
            
            ending = len(self.transactions)
            added = ending - starting
            imported = len(imported_transactions)
            deduped = imported - added
            print(f"Imported {imported}, Starting {starting}, ending {ending}, added {added}, deduped {deduped}")
                                       

        else:
            print("Overwriting self.transactions!")
            self.transactions = buys + sells + sends + receives

        for a in self.assets:
            asset_obj = Asset(symbol=a)
            assets.append(asset_obj)
        
        self.asset_objects = assets


        self.save(description="Imported from CSV")

        print(f"\nImported Transactions Saving to {save_as_filename}\n")

        return save_as_filename

    def first_transaction_date(self, asset=None):
        all_trans = {}
        
        for trans in self.transactions:

            # If asset is provided skip others
            if asset is not None:
                if trans.symbol != asset:
                    continue
            
            # Create key val for symbol
            if trans.symbol not in all_trans.keys():
                all_trans[trans.symbol] = []

            all_trans[trans.symbol].append(trans)

        # Sort By Time Stamp
        for key in all_trans.keys():
            all_trans[key].sort(key=lambda x: x.time_stamp)

        # Extract first transaction Date
        first_time_stamps = {}
        for key in all_trans.keys():
            first_time_stamps[key] = all_trans[key][0].time_stamp
            
            # print(first_time_stamps)
            # print(f"First Transaction Date for {key}: {all_trans[key][0].time_stamp}")

        return first_time_stamps

    def last_transaction_date(self, asset=None):
        all_trans = {}
        
        # Sort into Buys a Sells
        for trans in self.transactions:

            # If asset is provided only auto-link symbol provided
            if asset is not None:
                if trans.symbol != asset:
                    continue
            
            # Create key val for symbol
            if trans.symbol not in all_trans.keys():
                all_trans[trans.symbol] = []


            all_trans[trans.symbol].append(trans)

        
        # Sort By Time Stamp
        for key in all_trans.keys():
            all_trans[key].sort(key=lambda x: x.time_stamp)

        # Extract Last transaction Date
        last_time_stamps = {}
        for key in all_trans.keys():
            last_time_stamps[key] = all_trans[key][-1].time_stamp
            
        # print(last_time_stamps)
        # print(f"Last Transaction Date for {key}: {all_trans[key][-1].time_stamp}")

        return last_time_stamps


if __name__ == "__main__":

    transactions = Transactions()

    asset = "BTC"

    buys = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "buy"]
    sells = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "sell"]
    sends = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "send"]
    receives = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "receive"]

    buys.sort(key=lambda x: x.time_stamp)
    sends.sort(key=lambda x: x.time_stamp)
    receives.sort(key=lambda x: x.time_stamp)


    sent_quantity = 0.0
    received_quantity = 0.0
    bought_quantity = 0.0
    sold_quantity = 0.0
    sold_unlinked = 0.0
    bought_unlinked = 0.0

    for r in receives:
        received_quantity += r.quantity

    for send in sends:
        sent_quantity += send.quantity

    for b in buys:
        bought_quantity += b.quantity
        bought_unlinked += b.unlinked_quantity

    for s in sells:
        sold_quantity += s.quantity
        sold_unlinked += s.unlinked_quantity


    print(f"\n bought {bought_quantity} \n sent {sent_quantity} \n received {received_quantity} \n sold {sold_quantity} \n sold unlinked {sold_unlinked} \n bought unlinked {bought_unlinked}")


    transactions.auto_link(asset=None, algo='fifo')

    buys = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "buy"]
    sells = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "sell"]
    sends = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "send"]
    receives = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "receive"]

    buys.sort(key=lambda x: x.time_stamp)
    sends.sort(key=lambda x: x.time_stamp)
    receives.sort(key=lambda x: x.time_stamp)

    sent_quantity = 0.0
    received_quantity = 0.0
    bought_quantity = 0.0
    sold_quantity = 0.0
    sold_unlinked = 0.0
    bought_unlinked = 0.0

    for r in receives:
        received_quantity += r.quantity

    for send in sends:
        sent_quantity += send.quantity

    for b in buys:
        bought_quantity += b.quantity
        bought_unlinked += b.unlinked_quantity

    for s in sells:
        sold_quantity += s.quantity
        sold_unlinked += s.unlinked_quantity


    print(f"\n bought {bought_quantity} \n sent {sent_quantity} \n received {received_quantity} \n sold {sold_quantity} \n sold unlinked {sold_unlinked} \n bought unlinked {bought_unlinked}")

    
    filename = transactions.save()
    transactions.load(filename=filename)

    buys = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "buy"]
    sells = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "sell"]
    sends = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "send"]
    receives = [trans for trans in transactions if trans.symbol == asset and trans.trans_type == "receive"]

    buys.sort(key=lambda x: x.time_stamp)
    sends.sort(key=lambda x: x.time_stamp)
    receives.sort(key=lambda x: x.time_stamp)

    
    sent_quantity = 0.0
    received_quantity = 0.0
    bought_quantity = 0.0
    sold_quantity = 0.0
    sold_unlinked = 0.0
    bought_unlinked = 0.0

    for r in receives:
        received_quantity += r.quantity

    for send in sends:
        sent_quantity += send.quantity

    for b in buys:
        bought_quantity += b.quantity
        bought_unlinked += b.unlinked_quantity

    for s in sells:
        sold_quantity += s.quantity
        sold_unlinked += s.unlinked_quantity


    print(f"\n\n bought {bought_quantity} \n sent {sent_quantity} \n received {received_quantity} \n sold {sold_quantity} \n sold unlinked {sold_unlinked} \n bought unlinked {bought_unlinked}")

    





    



  
