# This module will handle parsing-related functions.

import pandas as pd
import dateutil
from openpyxl import load_workbook
from dateutil import parser
from dateutil.tz import gettz
from transaction import Buy, Sell, Send, Receive

# Define timezone mappings for dateutil.parser
tzinfos = {
    'PDT': -7 * 3600,  # Pacific Daylight Time
    'PST': -8 * 3600,  # Pacific Standard Time
    # Add other timezones as needed
}

# Add parsing functions here, e.g., for CSV/Excel files.

def import_transactions(file_path, transactions):
    """
    Imports transactions from a given file path and adds them to the Transactions object.

    Args:
        file_path (str): The path to the file containing transaction data.
        transactions (Transactions): The Transactions object to update.

    Returns:
        None
    """
    import pandas as pd
    from dateutil import parser
    import os

    try:
        trans_df = pd.read_csv(file_path)
        transactions_added = False
        
        for _, row in trans_df.iterrows():
            symbol = row['Asset Type']
            quantity = float(row['Asset Amount'])
            time_stamp = parser.parse(row['Date'], tzinfos=tzinfos)
            usd_spot = row['Asset Price']

            # Ensure usd_spot is a string before calling replace
            if isinstance(usd_spot, float):
                usd_spot = str(usd_spot)

            usd_spot = float(usd_spot.replace('$', '').replace(',', ''))
            
            # Ensure trans_type is a string before calling lower()
            trans_type = row['Transaction Type']
            if not isinstance(trans_type, str):
                trans_type = str(trans_type)
            trans_type = trans_type.lower()

            if trans_type == 'buy' or trans_type == 'bitcoin buy':
                transactions.transactions.append(Buy(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path))
                transactions_added = True
            elif trans_type == 'sell' or trans_type == 'bitcoin sale':
                transactions.transactions.append(Sell(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path))
                transactions_added = True
            elif trans_type == 'send' or trans_type == 'bitcoin withdrawal':
                transactions.transactions.append(Send(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path))
                transactions_added = True
            elif trans_type == 'receive' or trans_type == 'bitcoin deposit':
                transactions.transactions.append(Receive(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path))
                transactions_added = True
        
        # Save transactions if any were added
        if transactions_added:
            description = f"Imported from {os.path.basename(file_path)}"
            transactions.save(description=description)
            print(f"Transactions saved with description: {description}")
        else:
            print("No transactions were added from the file.")
            
    except Exception as e:
        print(f"Error importing transactions: {e}")