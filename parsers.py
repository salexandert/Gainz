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
    Prevents duplicate imports by checking for existing transactions with the same attributes.

    Args:
        file_path (str): The path to the file containing transaction data.
        transactions (Transactions): The Transactions object to update.

    Returns:
        tuple: (imported_count, skipped_count) Count of transactions imported and skipped due to duplicates.
    """
    import pandas as pd
    from dateutil import parser
    import os
    from decimal import Decimal, getcontext

    # Set precision for comparing float values
    getcontext().prec = 10
    
    # Function to check if a transaction is duplicate
    def is_duplicate(new_trans, existing_transactions, tolerance=1e-9):
        """Check if a transaction already exists in the collection."""
        for trans in existing_transactions:
            # Time difference less than 1 second (timestamps might have microsecond differences)
            time_match = abs((new_trans.time_stamp.replace(tzinfo=None) - 
                            trans.time_stamp.replace(tzinfo=None)).total_seconds()) < 1
            
            # Required attributes match
            if (trans.symbol == new_trans.symbol and
                abs(trans.quantity - new_trans.quantity) < tolerance and
                abs(trans.usd_spot - new_trans.usd_spot) < tolerance and
                trans.trans_type == new_trans.trans_type and
                time_match):
                return True
        return False

    try:
        trans_df = pd.read_csv(file_path)
        transactions_added = False
        imported_count = 0
        skipped_count = 0
        
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

            # Define keyword mappings for more flexible transaction type matching
            buy_keywords = ['buy', 'purchase']
            sell_keywords = ['sell', 'sale']
            send_keywords = ['send', 'withdrawal', 'withdraw']
            receive_keywords = ['receive', 'deposit', 'incoming']
            
            # Create temporary transaction object for duplicate checking
            temp_trans = None
            
            # Use a more flexible approach to check transaction type
            if any(keyword in trans_type for keyword in buy_keywords):
                temp_trans = Buy(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
            elif any(keyword in trans_type for keyword in sell_keywords):
                temp_trans = Sell(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
            elif any(keyword in trans_type for keyword in send_keywords):
                temp_trans = Send(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
            elif any(keyword in trans_type for keyword in receive_keywords):
                temp_trans = Receive(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
            else:
                print(f"Warning: Unrecognized transaction type '{row['Transaction Type']}' - skipping record")
                continue
            
            # Check for duplicates before adding
            if is_duplicate(temp_trans, transactions.transactions):
                print(f"Skipping duplicate transaction: {symbol} {quantity} {time_stamp}")
                skipped_count += 1
            else:
                transactions.transactions.append(temp_trans)
                transactions_added = True
                imported_count += 1
        
        # Save transactions if any were added
        if transactions_added:
            description = f"Imported from {os.path.basename(file_path)}"
            transactions.save(description=description)
            print(f"Transactions saved with description: {description}")
            print(f"Imported {imported_count} new transactions, skipped {skipped_count} duplicates")
        else:
            print("No transactions were added from the file.")
            print(f"Skipped {skipped_count} duplicate transactions")
            
        return (imported_count, skipped_count)
            
    except Exception as e:
        print(f"Error importing transactions: {e}")
        return (0, 0)