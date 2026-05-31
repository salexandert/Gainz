# This module will handle parsing-related functions.

import pandas as pd
import dateutil
import os
import re
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

COLUMN_ALIASES = {
    'date': [
        'date',
        'timestamp',
        'time',
        'datetime',
        'date time',
        'transaction date',
        'transaction time',
        'transaction timestamp',
        'posted date',
        'created at',
        'created date',
        'date utc',
        'timestamp utc',
    ],
    'transaction_id': [
        'id',
        'transaction id',
        'transaction identifier',
        'tx id',
        'txid',
        'trade id',
        'order id',
        'reference id',
    ],
    'transaction_type': [
        'transaction type',
        'type',
        'activity',
        'activity type',
        'action',
        'operation',
        'event type',
        'transaction',
        'description',
    ],
    'asset_type': [
        'asset type',
        'asset',
        'asset symbol',
        'asset ticker',
        'crypto asset',
        'crypto',
        'cryptocurrency',
        'coin',
        'coin symbol',
        'token',
        'token symbol',
        'symbol',
        'ticker',
        'base currency',
        'primary currency',
        'currency',
    ],
    'asset_amount': [
        'asset amount',
        'asset quantity',
        'quantity transacted',
        'quantity',
        'qty',
        'crypto amount',
        'crypto quantity',
        'coin amount',
        'coin quantity',
        'token amount',
        'token quantity',
        'amount transacted',
        'transaction quantity',
        'units',
        'shares',
    ],
    'asset_price': [
        'asset price',
        'price at transaction',
        'price',
        'spot price',
        'spot price usd',
        'asset price usd',
        'price per unit',
        'unit price',
        'execution price',
        'average price',
        'market price',
        'usd spot',
    ],
    'price_currency': [
        'price currency',
        'spot price currency',
        'asset price currency',
        'currency price',
        'fiat currency',
    ],
    'fiat_amount': [
        'amount',
        'fiat amount',
        'cash amount',
        'usd amount',
        'value',
        'transaction value',
        'gross amount',
    ],
    'net_amount': [
        'net amount',
        'net',
        'net value',
        'net proceeds',
        'settled amount',
    ],
    'fee': [
        'fee',
        'fees',
        'fees and or spread',
        'fee spread',
        'commission',
        'network fee',
    ],
    'subtotal': [
        'subtotal',
        'subtotal not including fees',
        'subtotal amount',
        'pre fee total',
        'pre fee amount',
    ],
    'total': [
        'total inclusive of fees and or spread',
        'total',
        'total amount',
        'total value',
        'amount usd',
        'net total',
    ],
    'notes': [
        'notes',
        'note',
        'memo',
        'details',
        'detail',
        'description',
        'comment',
    ],
}

TRANSACTION_TYPE_KEYWORDS = {
    'Buy': ['buy', 'bought', 'purchase', 'purchased', 'acquisition'],
    'Sell': ['sell', 'sold', 'sale', 'cash out'],
    'Send': ['send', 'sent', 'withdrawal', 'withdraw', 'transfer out', 'outgoing'],
    'Receive': ['receive', 'received', 'deposit', 'incoming', 'reward', 'staking', 'interest', 'airdrop'],
}

ASSET_NAME_ALIASES = {
    'bitcoin': 'BTC',
    'btc': 'BTC',
    'ethereum': 'ETH',
    'ether': 'ETH',
    'eth': 'ETH',
    'litecoin': 'LTC',
    'ltc': 'LTC',
    'bitcoin cash': 'BCH',
    'bch': 'BCH',
    'dogecoin': 'DOGE',
    'doge': 'DOGE',
    'solana': 'SOL',
    'sol': 'SOL',
    'cardano': 'ADA',
    'ada': 'ADA',
    'polygon': 'MATIC',
    'matic': 'MATIC',
    'avalanche': 'AVAX',
    'avax': 'AVAX',
    'chainlink': 'LINK',
    'link': 'LINK',
    'usd coin': 'USDC',
    'usdc': 'USDC',
    'tether': 'USDT',
    'usdt': 'USDT',
}

FIAT_ASSET_SYMBOLS = {'USD', 'US DOLLAR', 'US DOLLARS', 'DOLLAR', 'DOLLARS', '$'}


def parse_quantity_value(value):
    if pd.isna(value):
        return 0.0

    match = re.search(r'-?\d+(?:\.\d+)?', str(value).replace(',', ''))
    if not match:
        return 0.0

    return float(match.group(0))


def parse_money_value(value):
    if pd.isna(value):
        return 0.0

    text = str(value).replace('$', '').replace(',', '').strip()
    if text in ('', 'nan'):
        return 0.0

    match = re.search(r'-?\d+(?:\.\d+)?', text)
    if not match:
        return 0.0

    return float(match.group(0))


def normalize_column_name(value):
    text = str(value).lstrip('\ufeff').strip().lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _matches_header_heuristic(field, normalized_header):
    parts = set(normalized_header.split())

    if field == 'date':
        return ('date' in parts or 'time' in parts) and 'updated' not in parts
    if field == 'transaction_type':
        return (
            'type' in parts
            and ('transaction' in parts or 'activity' in parts or 'event' in parts or 'operation' in parts)
        )
    if field == 'asset_type':
        return 'asset' in parts and bool(parts & {'type', 'symbol', 'ticker', 'currency', 'coin', 'token'})
    if field == 'asset_amount':
        return (
            'quantity' in parts
            or 'qty' in parts
            or (bool(parts & {'asset', 'crypto', 'coin', 'token'}) and 'amount' in parts)
        )
    if field == 'asset_price':
        return 'price' in parts and 'currency' not in parts
    if field == 'fee':
        return 'fee' in parts or 'fees' in parts
    if field == 'notes':
        return bool(parts & {'note', 'notes', 'memo', 'detail', 'details', 'comment'})
    if field == 'subtotal':
        return 'subtotal' in parts
    if field == 'total':
        return 'total' in parts and 'subtotal' not in parts
    if field == 'net_amount':
        return 'net' in parts and 'amount' in parts
    if field == 'fiat_amount':
        return 'amount' in parts and not bool(parts & {'asset', 'crypto', 'coin', 'token'})

    return False


def build_column_lookup(columns):
    normalized_columns = [(column, normalize_column_name(column)) for column in columns]
    lookup = {}
    used_columns = set()

    for field, aliases in COLUMN_ALIASES.items():
        normalized_aliases = [normalize_column_name(alias) for alias in aliases]
        for alias in normalized_aliases:
            match = next(
                (
                    column
                    for column, normalized_column in normalized_columns
                    if column not in used_columns and normalized_column == alias
                ),
                None,
            )
            if match is not None:
                lookup[field] = match
                used_columns.add(match)
                break

    for field in COLUMN_ALIASES:
        if field in lookup:
            continue

        match = next(
            (
                column
                for column, normalized_column in normalized_columns
                if column not in used_columns and _matches_header_heuristic(field, normalized_column)
            ),
            None,
        )
        if match is not None:
            lookup[field] = match
            used_columns.add(match)

    return lookup


def get_row_value(row, column_lookup, field, default=None):
    column = column_lookup.get(field)
    if column is None:
        return default

    value = row.get(column, default)
    if pd.isna(value):
        return default

    return value


def normalize_asset_symbol(value):
    if pd.isna(value):
        return ''

    text = str(value).strip()
    if not text:
        return ''

    parenthetical = re.search(r'\(([A-Za-z0-9]{2,12})\)', text)
    if parenthetical:
        return parenthetical.group(1).upper()

    normalized = normalize_column_name(text)
    if normalized in ASSET_NAME_ALIASES:
        return ASSET_NAME_ALIASES[normalized]

    upper = text.upper().strip()
    if upper.endswith('-USD') or upper.endswith('/USD'):
        upper = upper[:-4]

    return re.sub(r'[^A-Z0-9]+', '', upper.split()[0])


def standardize_transaction_type(value):
    text = str(value).strip()
    normalized = normalize_column_name(text)

    for standard_type, keywords in TRANSACTION_TYPE_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return standard_type

    return text


def derive_asset_price(row, column_lookup, quantity):
    direct_price = parse_money_value(get_row_value(row, column_lookup, 'asset_price'))
    if direct_price:
        return direct_price

    for field in ('subtotal', 'total', 'net_amount', 'fiat_amount'):
        total_value = abs(parse_money_value(get_row_value(row, column_lookup, field)))
        if total_value and quantity:
            return total_value / abs(quantity)

    return 0.0


def _standard_row_from_lookup(row, column_lookup):
    quantity = parse_quantity_value(get_row_value(row, column_lookup, 'asset_amount'))

    return {
        'Asset Type': normalize_asset_symbol(get_row_value(row, column_lookup, 'asset_type')),
        'Transaction Type': standardize_transaction_type(get_row_value(row, column_lookup, 'transaction_type', '')),
        'Asset Amount': abs(quantity) if quantity < 0 else quantity,
        'Date': get_row_value(row, column_lookup, 'date'),
        'Asset Price': derive_asset_price(row, column_lookup, quantity),
    }


def transform_generic_to_standard(df):
    column_lookup = build_column_lookup(df.columns)
    required_fields = {'date', 'transaction_type', 'asset_type', 'asset_amount'}

    if not required_fields.issubset(column_lookup):
        return df

    result_df = pd.DataFrame([_standard_row_from_lookup(row, column_lookup) for _, row in df.iterrows()])
    result_df = result_df[
        result_df['Asset Type'].notna()
        & (result_df['Asset Type'] != '')
        & ~result_df['Asset Type'].isin(FIAT_ASSET_SYMBOLS)
    ]

    return result_df


def parse_coinbase_convert_note(note):
    match = re.search(
        r'Converted\s+([0-9,]+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+to\s+([0-9,]+(?:\.\d+)?)\s+([A-Za-z0-9]+)',
        str(note),
        re.IGNORECASE,
    )
    if not match:
        return None

    return {
        'from_quantity': parse_quantity_value(match.group(1)),
        'from_asset': match.group(2).upper(),
        'to_quantity': parse_quantity_value(match.group(3)),
        'to_asset': match.group(4).upper(),
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
        header = pd.read_csv(file_path, nrows=0).columns.tolist()
        column_lookup = build_column_lookup(header)
        normalized_headers = {normalize_column_name(header_name) for header_name in header}
        filename_hint = normalize_column_name(os.path.basename(file_path))

        common_fields = ['date', 'transaction_type', 'asset_type', 'asset_amount', 'asset_price']
        cash_app_markers = {'transaction id', 'net amount', 'asset type', 'asset amount'}
        coinbase_markers = {
            'quantity transacted',
            'price currency',
            'price at transaction',
            'total inclusive of fees and or spread',
            'notes',
        }

        cash_app_match = sum(1 for field in common_fields if field in column_lookup)
        cash_app_match += sum(1 for marker in cash_app_markers if marker in normalized_headers)
        coinbase_match = sum(1 for field in common_fields if field in column_lookup)
        coinbase_match += sum(1 for marker in coinbase_markers if marker in normalized_headers)

        if 'cash app' in filename_hint or 'cashapp' in filename_hint:
            cash_app_match += 2
        if 'coinbase' in filename_hint:
            coinbase_match += 2

        if cash_app_match >= 6 and cash_app_match >= coinbase_match:
            return 'cashapp'
        elif coinbase_match >= 6:
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
    column_lookup = build_column_lookup(df.columns)
    result_df = pd.DataFrame([_standard_row_from_lookup(row, column_lookup) for _, row in df.iterrows()])

    # Filter out rows with empty Asset Type or fiat-only activity.
    result_df = result_df[
        result_df['Asset Type'].notna()
        & (result_df['Asset Type'] != '')
        & ~result_df['Asset Type'].isin(FIAT_ASSET_SYMBOLS)
    ]

    return result_df


def transform_coinbase_to_standard(df):
    """
    Transforms Coinbase CSV format to the standard format expected by import_transactions.
    
    Args:
        df (DataFrame): Coinbase dataframe
        
    Returns:
        DataFrame: Transformed dataframe with standardized column names
    """
    rows = []
    column_lookup = build_column_lookup(df.columns)

    for _, row in df.iterrows():
        asset = normalize_asset_symbol(get_row_value(row, column_lookup, 'asset_type'))
        trans_type = str(get_row_value(row, column_lookup, 'transaction_type', ''))
        trans_type_lower = trans_type.lower()
        timestamp = get_row_value(row, column_lookup, 'date')
        quantity = parse_quantity_value(get_row_value(row, column_lookup, 'asset_amount'))
        asset_price = derive_asset_price(row, column_lookup, quantity)

        if 'convert' in trans_type_lower:
            convert = parse_coinbase_convert_note(get_row_value(row, column_lookup, 'notes'))
            if convert:
                conversion_total = (
                    parse_money_value(get_row_value(row, column_lookup, 'total'))
                    or parse_money_value(get_row_value(row, column_lookup, 'subtotal'))
                    or (convert['from_quantity'] * asset_price)
                )

                sell_spot = conversion_total / convert['from_quantity'] if convert['from_quantity'] else asset_price
                buy_spot = conversion_total / convert['to_quantity'] if convert['to_quantity'] else 0.0

                rows.append({
                    'Asset Type': convert['from_asset'],
                    'Transaction Type': 'Sell',
                    'Asset Amount': abs(convert['from_quantity']),
                    'Date': timestamp,
                    'Asset Price': sell_spot,
                })
                rows.append({
                    'Asset Type': convert['to_asset'],
                    'Transaction Type': 'Buy',
                    'Asset Amount': abs(convert['to_quantity']),
                    'Date': timestamp,
                    'Asset Price': buy_spot,
                })
                continue

        standard_type = standardize_transaction_type(trans_type)

        if pd.isna(asset) or asset == '' or asset in FIAT_ASSET_SYMBOLS:
            continue

        if standard_type in ('Sell', 'Send') or quantity < 0:
            quantity = abs(quantity)

        rows.append({
            'Asset Type': asset,
            'Transaction Type': standard_type,
            'Asset Amount': quantity,
            'Date': timestamp,
            'Asset Price': asset_price,
        })

    return pd.DataFrame(rows)

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
    from decimal import Decimal
    import logging
    
    # Function to check if a transaction is duplicate
    def is_duplicate(new_trans, existing_transactions, tolerance=1e-6):
        """Check if a transaction already exists in the collection."""
        for trans in existing_transactions:
            # Skip if different symbols or transaction types
            if trans.symbol != new_trans.symbol or trans.trans_type != new_trans.trans_type:
                continue
                
            # Calculate the time difference, but normalize within a day for timezone issues
            time_diff_seconds = abs((new_trans.time_stamp.replace(tzinfo=None) - 
                                  trans.time_stamp.replace(tzinfo=None)).total_seconds())
            
            # Check for specific timezone offsets (+/- 7 or 8 hours), which are common in PST/UTC conversions
            pst_utc_diff = abs(abs(time_diff_seconds) - (7 * 3600)) < 60  # Within 1 minute of 7 hour difference
            pdt_utc_diff = abs(abs(time_diff_seconds) - (8 * 3600)) < 60  # Within 1 minute of 8 hour difference
              # Check for same-day transactions (within 24h) or near-identical times (within 5 minutes) for timezone conversions
            same_time_diff = time_diff_seconds < 300  # 5 minutes
            timezone_diff = abs(time_diff_seconds % 86400) < 300  # 5 minutes within same time of day
            time_match = same_time_diff or timezone_diff or pst_utc_diff or pdt_utc_diff
            
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
            trans_df = transform_generic_to_standard(raw_df)
            if trans_df is raw_df:
                print("Warning: Unknown CSV format. Attempting to process as-is.")
        
        transactions_added = False
        imported_count = 0
        skipped_count = 0
        import_warnings = []
        
        for row_number, (_, row) in enumerate(trans_df.iterrows(), start=2):
            try:
                symbol = normalize_asset_symbol(row['Asset Type'])
                if not symbol or symbol in FIAT_ASSET_SYMBOLS:
                    warning = (
                        f"Skipped row {row_number} from {os.path.basename(file_path)}: "
                        f"missing or non-crypto asset '{row['Asset Type']}'"
                    )
                    print(f"Warning: {warning}")
                    import_warnings.append(warning)
                    continue

                quantity = parse_quantity_value(row['Asset Amount'])
                time_stamp = parser.parse(row['Date'], tzinfos=tzinfos)
                usd_spot = parse_money_value(row['Asset Price'])
                
                # Ensure trans_type is a string before calling lower()
                trans_type = row['Transaction Type']
                if not isinstance(trans_type, str):
                    trans_type = str(trans_type)
                trans_type = normalize_column_name(trans_type)

                # Create temporary transaction object for duplicate checking
                temp_trans = None

                # Use a more flexible approach to check transaction type
                if any(keyword in trans_type for keyword in TRANSACTION_TYPE_KEYWORDS['Buy']):
                    temp_trans = Buy(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
                elif any(keyword in trans_type for keyword in TRANSACTION_TYPE_KEYWORDS['Sell']):
                    temp_trans = Sell(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
                elif any(keyword in trans_type for keyword in TRANSACTION_TYPE_KEYWORDS['Send']):
                    temp_trans = Send(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
                elif any(keyword in trans_type for keyword in TRANSACTION_TYPE_KEYWORDS['Receive']):
                    temp_trans = Receive(symbol=symbol, quantity=quantity, time_stamp=time_stamp, usd_spot=usd_spot, source=file_path)
                else:
                    warning = (
                        f"Skipped row {row_number} from {os.path.basename(file_path)}: "
                        f"unrecognized transaction type '{row['Transaction Type']}'"
                    )
                    print(f"Warning: {warning}")
                    import_warnings.append(warning)
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
                warning = f"Skipped row {row_number} from {os.path.basename(file_path)}: missing required column {ke}"
                print(f"Error processing row: {warning}")
                import_warnings.append(warning)
                continue
            except Exception as e:
                warning = f"Skipped row {row_number} from {os.path.basename(file_path)}: {e}"
                print(f"Error processing row: {warning}")
                import_warnings.append(warning)
                continue

        existing_warnings = getattr(transactions, 'import_warnings', [])
        transactions.import_warnings = existing_warnings + import_warnings
        transactions.last_import_result = {
            "file_path": file_path,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "warnings": import_warnings,
        }

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
