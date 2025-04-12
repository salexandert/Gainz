# This module will handle parsing-related functions.

import pandas as pd
import dateutil
import os
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

def detect_csv_format(file_path):
    """
    Detects the CSV format by examining the header row.
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        str: 'cashapp', 'coinbase', or 'unknown'
    """
    try:
        # Read just the header row
        header = pd.read_csv(file_path, nrows=0).columns.tolist()
        
        # Check for Cash App format (case-insensitive comparison)
        cash_app_headers = ['date', 'transaction id', 'transaction type', 'currency', 
                           'amount', 'asset type', 'asset price', 'asset amount']
        
        # Check for Coinbase format (case-insensitive comparison)
        coinbase_headers = ['timestamp', 'transaction type', 'asset', 
                           'quantity transacted', 'price currency', 'price at transaction']
        
        # Convert headers to lowercase for case-insensitive comparison
        header_lower = [h.lower() for h in header]
        
        # Check if most of the expected Cash App headers are present
        cash_app_match = sum(1 for h in cash_app_headers if h in header_lower)
        coinbase_match = sum(1 for h in coinbase_headers if h in header_lower)
        
        if cash_app_match >= 5:  # At least 5 matching headers
            return 'cashapp'
        elif coinbase_match >= 4:  # At least 4 matching headers
            return 'coinbase'
        else:
            return 'unknown'
    except Exception as e:
        print(f"Error detecting CSV format: {e}")
        return 'unknown'

def transform_cashapp_to_standard(df):
    """
    Transforms Cash App CSV format to the standard format expected by import_transactions.
    
    Args:
        df (DataFrame): Cash App dataframe
        
    Returns:
        DataFrame: Transformed dataframe with standardized column names
    """
    result_df = pd.DataFrame()
    
    # Map Cash App CSV columns to standard columns
    result_df['Asset Type'] = df['Asset Type']
    
    # Process Transaction Type
    result_df['Transaction Type'] = df['Transaction Type'].apply(
        lambda x: 'Buy' if 'buy' in str(x).lower() else
                 'Sell' if 'sell' in str(x).lower() else
                 'Send' if 'sent' in str(x).lower() else
                 'Receive' if 'received' in str(x).lower() or 'deposit' in str(x).lower() else x
    )

    # Process Asset Amount - ensure sell/send values are positive
    result_df['Asset Amount'] = df.apply(
        lambda row: abs(float(row['Asset Amount'])) if pd.notna(row['Asset Amount']) and 
                    (('sell' in str(row['Transaction Type']).lower()) or 
                     ('sent' in str(row['Transaction Type']).lower()))
                    else row['Asset Amount'], 
        axis=1
    )
    
    result_df['Date'] = df['Date']
    result_df['Asset Price'] = df['Asset Price']
    
    # Filter out rows with empty Asset Type (non-crypto transactions)
    result_df = result_df[result_df['Asset Type'].notna() & (result_df['Asset Type'] != '')]
    
    return result_df

def transform_coinbase_to_standard(df):
    """
    Transforms Coinbase CSV format to the standard format expected by import_transactions.
    
    Args:
        df (DataFrame): Coinbase dataframe
        
    Returns:
        DataFrame: Transformed dataframe with standardized column names
    """
    result_df = pd.DataFrame()
    
    # Map Coinbase CSV columns to standard columns
    result_df['Asset Type'] = df['Asset']
    
    # Process Transaction Type
    result_df['Transaction Type'] = df['Transaction Type'].apply(
        lambda x: 'Buy' if 'buy' in str(x).lower() else
                 'Sell' if 'sell' in str(x).lower() else
                 'Send' if 'send' in str(x).lower() or 'withdraw' in str(x).lower() else
                 'Receive' if 'receive' in str(x).lower() or 'deposit' in str(x).lower() or 'reward' in str(x).lower() or 'staking' in str(x).lower() else x
    )
    
    # Process Asset Amount - ensure sell/send values are positive
    result_df['Asset Amount'] = df.apply(
        lambda row: abs(float(row['Quantity Transacted'])) if pd.notna(row['Quantity Transacted']) and
                   (('sell' in str(row['Transaction Type']).lower()) or 
                    ('send' in str(row['Transaction Type']).lower()) or
                    ('withdraw' in str(row['Transaction Type']).lower()) or
                    float(str(row['Quantity Transacted']).replace(',', '')) < 0)
                   else row['Quantity Transacted'],
        axis=1
    )
    
    result_df['Date'] = df['Timestamp']
    
    # Process Price at Transaction (remove $ and spaces)
    result_df['Asset Price'] = df['Price at Transaction'].apply(
        lambda x: str(x).replace('$', '').replace(' ', '') if pd.notna(x) else '0'
    )
    
    # Filter out rows with empty Asset Type (non-crypto transactions)
    result_df = result_df[result_df['Asset Type'].notna() & (result_df['Asset Type'] != '')]
    
    return result_df

def import_transactions(file_path, transactions):
    """
    Imports transactions from a given file path and adds them to the Transactions object.
    Prevents duplicate imports by checking for existing transactions with the same attributes.
    Now handles multiple CSV formats automatically.

    Args:
        file_path (str): The path to the file containing transaction data.
        transactions (Transactions): The Transactions object to update.

    Returns:
        tuple: (imported_count, skipped_count) Count of transactions imported and skipped due to duplicates.
    """
    from decimal import Decimal, getcontext    # Set precision for comparing float values
    getcontext().prec = 10
    
    # Function to check if a transaction is duplicate      def is_duplicate(new_trans, existing_transactions, tolerance=1e-6):
        """Check if a transaction already exists in the collection."""
        for trans in existing_transactions:
            # Skip if different symbols or transaction types
            if trans.symbol != new_trans.symbol or trans.trans_type != new_trans.trans_type:
                continue
                
            # Calculate the time difference, but normalize within a day for timezone issues
            time_diff_seconds = abs((new_trans.time_stamp.replace(tzinfo=None) - 
                                  trans.time_stamp.replace(tzinfo=None)).total_seconds())
            
            # Check for same-day transactions (within 24h) or near-identical times (within 1 minute) for timezone conversions
            # Use timestamp difference modulo 24 hours to detect timezone differences
            same_time_diff = time_diff_seconds < 300  # 5 minutes
            timezone_diff = abs(time_diff_seconds % 86400) < 300  # 5 minutes within same time of day
            time_match = same_time_diff or timezone_diff
            
            # Required attributes match with relaxed tolerance for quantity
            quantity_match = abs(trans.quantity - new_trans.quantity) < max(tolerance, tolerance * trans.quantity)
            # More relaxed tolerance for price (0.5% difference is acceptable for price variations)
            usd_match = abs(trans.usd_spot - new_trans.usd_spot) < max(0.005 * trans.usd_spot, tolerance * trans.usd_spot)
              # For debugging - use logging instead of print statements
            if (trans.symbol == new_trans.symbol and quantity_match and trans.trans_type == new_trans.trans_type):
                # Get logger for parsers
                import logging
                logger = logging.getLogger('parsers')
                logger.debug(f"Potential duplicate found: {trans.symbol} {trans.quantity} @ {trans.time_stamp} vs {new_trans.quantity} @ {new_trans.time_stamp}")
                logger.debug(f"Time diff: {time_diff_seconds} seconds, time_match: {time_match}")
            
            if (trans.symbol == new_trans.symbol and
                quantity_match and
                usd_match and
                trans.trans_type == new_trans.trans_type and
                time_match):
                # Get logger for parsers
                import logging
                logger = logging.getLogger('parsers')
                logger.info(f"Found duplicate: {new_trans.symbol} {new_trans.quantity} vs {trans.quantity}, diff={abs(trans.quantity - new_trans.quantity)}")
                return True
        return False

    try:
        # Detect the CSV format
        csv_format = detect_csv_format(file_path)
        print(f"Detected CSV format: {csv_format}")
        
        # Read the CSV file
        raw_df = pd.read_csv(file_path)
        
        # Transform to standard format based on detected format
        if csv_format == 'cashapp':
            trans_df = transform_cashapp_to_standard(raw_df)
        elif csv_format == 'coinbase':
            trans_df = transform_coinbase_to_standard(raw_df)
        else:
            # Try to use original format as a fallback
            trans_df = raw_df
            print("Warning: Unknown CSV format. Attempting to process as-is.")
        
        transactions_added = False
        imported_count = 0
        skipped_count = 0
        
        for _, row in trans_df.iterrows():
            try:
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
                receive_keywords = ['receive', 'deposit', 'incoming', 'reward', 'staking']
                
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
                    # Use logger instead of print
                    import logging
                    logger = logging.getLogger('parsers')
                    logger.info(f"Skipping duplicate transaction: {symbol} {quantity} {time_stamp}")
                    skipped_count += 1
                else:
                    transactions.transactions.append(temp_trans)
                    transactions_added = True
                    imported_count += 1
            except KeyError as ke:
                print(f"Error processing row: Missing required column - {ke}")
                continue
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
          # Save transactions if any were added
        if transactions_added:
            description = f"Imported from {os.path.basename(file_path)}"
            transactions.save(description=description)
            # Use logger instead of print
            import logging
            logger = logging.getLogger('parsers')
            logger.info(f"Transactions saved with description: {description}")
            logger.info(f"Imported {imported_count} new transactions, skipped {skipped_count} duplicates")
        else:
            # Use logger instead of print
            import logging
            logger = logging.getLogger('parsers')
            logger.info("No transactions were added from the file.")
            logger.info(f"Skipped {skipped_count} duplicate transactions")
            
        return (imported_count, skipped_count)
            
    except Exception as e:
        print(f"Error importing transactions: {e}")
        return (0, 0)