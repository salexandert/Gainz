import os
import zipfile
from openpyxl import load_workbook
import pandas as pd
from conversion import Conversion
from transaction import Buy, Sell, Send, Receive
from assets import Asset
from time import strftime

# Define the base directory for the project
basedir = os.path.dirname(__file__)

# Updated imports to reflect the new modular structure
from parsers import *
from filters import *
from linking import *
from utils import *
from functools import lru_cache

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

    def load_saves(self):
        saves = []
        revision_num = None

        match_object = "saved_"

        view_num = 1
        for root, dirs, files in os.walk(os.path.join(basedir, 'saves')):
            for f in files:

                save_as_filename = os.path.join(basedir, 'saves', f)
                if match_object in f and f.endswith('xlsx'):
                    # Check if the file is a valid zip file
                    if not zipfile.is_zipfile(save_as_filename):
                        print(f"File {save_as_filename} is not a zip file")
                        continue
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

    def load(self, filename=None):
        # Check if the file is a valid zip file
        if not zipfile.is_zipfile(filename):
            raise zipfile.BadZipFile(f"File {filename} is not a zip file")

        workbook = load_workbook(filename=filename)
        if 'Description' in workbook.sheetnames:
            sheet = workbook['Description']
            description = sheet.cell(column=1, row=1).value
            revision_num = sheet.cell(column=2, row=1).value
            if revision_num is not None:
                self.revision_num = revision_num

        # Read Previously saved data into pandas df - Transactions    
        trans_df = pd.read_excel(filename, sheet_name='All Transactions', converters = {'my_str_column': list})
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
            # Check if 'fee' column exists before accessing it
            if 'fee' in row:
                trans_obj.fee = row['fee']
            sells.append(trans_obj)

        # Load Buys
        for index, row in buy_df.iterrows():
            trans_obj = Buy(symbol=row['symbol'], quantity=row['quantity'], time_stamp=row['time_stamp'], usd_spot=row['usd_spot'],  source=row['source'])
            # Check if 'fee' column exists before accessing it
            if 'fee' in row:
                trans_obj.fee = row['fee']
            buys.append(trans_obj)

        # Load Sends
        for index, row in send_df.iterrows():
            sends.append(Send(symbol=row['symbol'], quantity=row['quantity'], time_stamp=row['time_stamp'], usd_spot=row['usd_spot'],  source=row['source']))

        # Load Receives
        for index, row in receive_df.iterrows():
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

        # Multi-Link Indicators
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
                    if trans.trans_type == 'sell':
                        sell_obj = trans

                elif trans.name == buy:
                    if trans.trans_type == 'buy':
                        buy_obj = trans

                if buy_obj and sell_obj:
                    break
            
            if sell_obj and buy_obj:
                sell_obj.link_transaction(buy_obj, link_quantity=quantity)

        return list(transactions)

    def save(self, description=None):
        save_as_filename = os.path.join(basedir, "saves", f"saved_{strftime('Y%Y-M%m-D%d_H%H-M%M-S%S')}.xlsx")
        
        for trans in self.transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()
            trans.time_stamp = trans.time_stamp.replace(tzinfo=None)
            for link in trans.links:
                link.buy.time_stamp = link.buy.time_stamp.replace(tzinfo=None)
                link.sell.time_stamp = link.sell.time_stamp.replace(tzinfo=None)
        
        trans_df = pd.DataFrame([vars(s) for s in self.transactions])
        conversion_df = pd.DataFrame([vars(s) for s in self.conversions])
        asset_df = pd.DataFrame([vars(s) for s in self.asset_objects])

        with pd.ExcelWriter(save_as_filename,  engine = 'xlsxwriter') as writer:
            trans_df.to_excel(writer, sheet_name="All Transactions")
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

    def first_transaction_date(self, asset=None):
        """
        Returns a dictionary with the first transaction date for each asset or a specific asset.

        Args:
            asset (str, optional): The symbol of the asset to get the first transaction date for. 
                                   If None, returns dates for all assets. Defaults to None.

        Returns:
            dict: A dictionary with asset symbols as keys and their first transaction dates as values.
        """
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
            all_trans[key].sort(key=lambda x: x.time_stamp.replace(tzinfo=None))

        # Extract first transaction Date
        first_time_stamps = {}
        for key in all_trans.keys():
            first_time_stamps[key] = all_trans[key][0].time_stamp.replace(tzinfo=None)
            
        return first_time_stamps

    def last_transaction_date(self, asset=None):
        """
        Returns a dictionary with the last transaction date for each asset or a specific asset.

        Args:
            asset (str, optional): The symbol of the asset to get the last transaction date for. 
                                  If None, returns dates for all assets. Defaults to None.

        Returns:
            dict: A dictionary with asset symbols as keys and their last transaction dates as values.
        """
        all_trans = {}

        # Sort into Buys a Sells
        for trans in self.transactions:
            # If asset is provided only filter for specified asset
            if asset is not None:
                if trans.symbol != asset:
                    continue
            
            # Create key val for symbol
            if trans.symbol not in all_trans.keys():
                all_trans[trans.symbol] = []

            all_trans[trans.symbol].append(trans)

        # Sort By Time Stamp
        for key in all_trans.keys():
            all_trans[key].sort(key=lambda x: x.time_stamp.replace(tzinfo=None))

        # Extract Last transaction Date
        last_time_stamps = {}
        for key in all_trans.keys():
            last_time_stamps[key] = all_trans[key][-1].time_stamp.replace(tzinfo=None)

        return last_time_stamps

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
            list: A list of dictionaries containing information about any failures that occurred during linking.
        """
        
        sells = {}
        buys = {}
        min_unlinked = 0.0000001

        # failures is a list of dicts
        failures = []

        # Sort into Buys and Sells
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
            if year is not None and year != 'All Time':
                date_range = {
                    'start_date': f"01/01/{year} 12:00 AM",
                    'end_date': f"12/31/{year} 11:59 PM"
                    }

                from dateutil import parser
                
                try:
                    # Try to import whois_timezone_info or use a default
                    try:
                        from parsers import tzinfos
                    except ImportError:
                        tzinfos = {
                            'PDT': -7 * 3600,  # Pacific Daylight Time
                            'PST': -8 * 3600,  # Pacific Standard Time
                        }
                        
                    start_date = parser.parse(date_range['start_date'], tzinfos=tzinfos)
                    end_date = parser.parse(date_range['end_date'], tzinfos=tzinfos)
                    
                    # Filter Transactions to date range
                    for key in sells.keys():
                        filtered_transactions = []
                        for trans in sells[key]:
                            if isinstance(trans.time_stamp, str):
                                trans_time_stamp = parser.parse(trans.time_stamp, tzinfos=tzinfos)
                            else:
                                trans_time_stamp = trans.time_stamp
                            
                            # Make all timestamps timezone-naive for comparison
                            if hasattr(trans_time_stamp, 'tzinfo') and trans_time_stamp.tzinfo:
                                trans_time_stamp = trans_time_stamp.replace(tzinfo=None)
                            if hasattr(start_date, 'tzinfo') and start_date.tzinfo:
                                start_date = start_date.replace(tzinfo=None)
                            if hasattr(end_date, 'tzinfo') and end_date.tzinfo:
                                end_date = end_date.replace(tzinfo=None)
                                
                            if trans_time_stamp >= start_date and trans_time_stamp <= end_date:              
                                filtered_transactions.append(trans)

                        sells[key] = filtered_transactions
                        
                except Exception as e:
                    print(f"Error filtering by year: {e}")
        
        # sort for algo types
        if algo == 'fifo':
            # sort buys and sells by time_stamp
            for key in buys.keys():
                buys[key].sort(key=lambda x: x.time_stamp.replace(tzinfo=None) if hasattr(x.time_stamp, 'replace') else x.time_stamp)
            
            for key in sells.keys():
                sells[key].sort(key=lambda x: x.time_stamp.replace(tzinfo=None) if hasattr(x.time_stamp, 'replace') else x.time_stamp)

            from utils import round_decimals_down
            
            keys = list(sells.keys())
            keys.sort()
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
                            buy_time = buy.time_stamp.replace(tzinfo=None) if hasattr(buy.time_stamp, 'replace') else buy.time_stamp
                            sell_time = sell.time_stamp.replace(tzinfo=None) if hasattr(sell.time_stamp, 'replace') else sell.time_stamp
                            
                            if buy_time >= sell_time:
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

                            # if the link is less than $1.00 skip it
                            if abs(profit) < 1.0:
                                continue
                            
                            link = sell.link_transaction(buy, link_quantity)
                            links.append(link)
                            quantity_linked += link.quantity

                        if (sell.unlinked_quantity * sell.usd_spot) > min_unlinked:
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
                sells[key].sort(key=lambda x: x.time_stamp.replace(tzinfo=None) if hasattr(x.time_stamp, 'replace') else x.time_stamp)

            from utils import round_decimals_down
            
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
                            buy_time = buy.time_stamp.replace(tzinfo=None) if hasattr(buy.time_stamp, 'replace') else buy.time_stamp
                            sell_time = sell.time_stamp.replace(tzinfo=None) if hasattr(sell.time_stamp, 'replace') else sell.time_stamp
                            
                            if buy_time >= sell_time:
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
                            failures.append({
                                'asset': sell.symbol, 
                                'unlinkable': sell.unlinked_quantity,
                                'quantity': sell.quantity,
                                'timestamp': sell.time_stamp,
                                'algo': algo
                            })

        # Update transactions after linking
        for trans in self.transactions:
            trans.update_linked_transactions()
            trans.set_multi_link()
            
        return failures

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

    transactions.import_transactions('LOCAL_TAX_FILE_REMOVED')

@lru_cache(maxsize=1024)
def calculate_gain(sell, buy):
    return sell.usd_spot * sell.quantity - buy.usd_spot * buy.quantity













