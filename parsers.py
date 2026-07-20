# This module will handle parsing-related functions.

import csv
import hashlib
import logging
import pandas as pd
import os
import re
from decimal import Decimal, InvalidOperation
from openpyxl import load_workbook
from date_parsing import parse_gainz_datetime
from transaction import Buy, Sell, Send, Receive

parsers_logger = logging.getLogger('parsers')

NUMERIC_RE = re.compile(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?')
INPUT_RELIABILITY_BLOCKER_PREFIX = "INPUT RELIABILITY BLOCKER:"

COINBASE_RAW_COLUMNS = {
    'asset acquired',
    'quantity acquired bought received etc',
    'cost basis incl fees and or spread usd',
    'asset disposed sold sent etc',
    'quantity disposed',
    'proceeds excl fees and or spread usd',
}

LEDGER_LIVE_COLUMNS = {
    'operation date',
    'currency ticker',
    'operation type',
    'operation amount',
    'operation fees',
    'operation hash',
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
        'spot price at transaction',
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
    'fee_currency': [
        'fee currency',
        'fee asset',
        'fee unit',
        'commission currency',
        'commission asset',
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
        'total inclusive of fees and spread',
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
    'Buy': ['buy', 'bought', 'purchase', 'purchased', 'acquire', 'acquired', 'acquisition'],
    'Sell': ['sell', 'sold', 'sale', 'cash out', 'dispose', 'disposed', 'disposition', 'spend', 'spent', 'payment'],
    'Send': ['send', 'sent', 'withdrawal', 'withdraw', 'transfer out', 'outgoing'],
    'Receive': ['receive', 'received', 'deposit', 'incoming', 'reward', 'staking', 'interest', 'airdrop', 'earn', 'coinbase earn'],
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
STANDARD_IMPORT_COLUMNS = {'Asset Type', 'Asset Amount', 'Date', 'Asset Price', 'Transaction Type'}
REQUIRED_IMPORT_FIELDS = ['date', 'transaction_type', 'asset_type', 'asset_amount']
PRICING_IMPORT_FIELDS = ['asset_price', 'subtotal', 'total', 'net_amount', 'fiat_amount']
IMPORT_MAPPING_FIELDS = [
    {'field': 'date', 'label': 'Date/time', 'required': True},
    {'field': 'transaction_type', 'label': 'Transaction type', 'required': True},
    {'field': 'asset_type', 'label': 'Asset symbol', 'required': True},
    {'field': 'asset_amount', 'label': 'Asset quantity', 'required': True},
    {'field': 'asset_price', 'label': 'USD spot price per unit', 'required': False},
    {'field': 'fiat_amount', 'label': 'Gross USD value', 'required': False},
    {'field': 'fee', 'label': 'Fee or spread', 'required': False},
    {'field': 'fee_currency', 'label': 'Fee currency or asset', 'required': False},
    {'field': 'subtotal', 'label': 'Subtotal before fees', 'required': False},
    {'field': 'total', 'label': 'Total including fees', 'required': False},
    {'field': 'net_amount', 'label': 'Net amount after fees', 'required': False},
    {'field': 'notes', 'label': 'Notes/details', 'required': False},
]


def parse_quantity_value(value):
    if pd.isna(value):
        return 0.0

    text = str(value).replace(',', '').strip()
    match = NUMERIC_RE.search(text)
    if not match:
        return 0.0

    try:
        parsed = Decimal(match.group(0))
    except InvalidOperation:
        return 0.0

    if text.startswith('(') and text.endswith(')'):
        parsed = -abs(parsed)
    return float(parsed)


def parse_money_value(value):
    if pd.isna(value):
        return 0.0

    text = str(value).replace('$', '').replace(',', '').strip()
    if text in ('', 'nan'):
        return 0.0

    match = NUMERIC_RE.search(text)
    if not match:
        return 0.0

    try:
        parsed = Decimal(match.group(0))
    except InvalidOperation:
        return 0.0

    if str(value).strip().startswith('(') and str(value).strip().endswith(')'):
        parsed = -abs(parsed)
    return float(parsed)


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


def _actual_column_name(columns, selected_column):
    selected_normalized = normalize_column_name(selected_column)

    for column in columns:
        if column == selected_column or normalize_column_name(column) == selected_normalized:
            return column

    return None


def build_column_lookup(columns, column_mapping=None):
    normalized_columns = [(column, normalize_column_name(column)) for column in columns]
    lookup = {}
    used_columns = set()

    if column_mapping:
        for field, selected_column in column_mapping.items():
            if field not in COLUMN_ALIASES or not selected_column:
                continue

            actual_column = _actual_column_name(columns, selected_column)
            if actual_column is not None:
                lookup[field] = actual_column
                used_columns.add(actual_column)

    for field, aliases in COLUMN_ALIASES.items():
        if field in lookup:
            continue

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


def get_import_column_status(columns, column_mapping=None):
    column_lookup = build_column_lookup(columns, column_mapping=column_mapping)
    missing_required = [
        field
        for field in REQUIRED_IMPORT_FIELDS
        if field not in column_lookup
    ]
    has_pricing = any(field in column_lookup for field in PRICING_IMPORT_FIELDS)

    return {
        'can_import': len(missing_required) == 0,
        'missing_required': missing_required,
        'has_pricing': has_pricing,
        'column_lookup': column_lookup,
        'score': len(REQUIRED_IMPORT_FIELDS) - len(missing_required) + (1 if has_pricing else 0),
    }


def build_column_mapping_suggestions(columns):
    column_lookup = build_column_lookup(columns)
    suggestions = {}

    for field_config in IMPORT_MAPPING_FIELDS:
        field = field_config['field']
        suggestions[field] = column_lookup.get(field, '')

    if not suggestions.get('fiat_amount'):
        for pricing_field in ('total', 'subtotal', 'net_amount', 'fiat_amount'):
            if pricing_field in column_lookup:
                suggestions['fiat_amount'] = column_lookup[pricing_field]
                break

    return suggestions


def get_import_mapping_fields():
    return [field.copy() for field in IMPORT_MAPPING_FIELDS]


def read_csv_columns(file_path, header_row=1):
    skiprows = max(int(header_row or 1) - 1, 0)
    return pd.read_csv(file_path, skiprows=skiprows, nrows=0).columns.tolist()


def _scan_csv_header_rows(file_path, max_rows=12):
    candidates = []

    with open(file_path, newline='', encoding='utf-8-sig', errors='replace') as file:
        reader = csv.reader(file)

        for row_number, row in enumerate(reader, start=1):
            if row_number > max_rows:
                break

            cleaned_row = [cell.strip() for cell in row]
            if not any(cleaned_row):
                continue

            status = get_import_column_status(cleaned_row)
            candidates.append({
                'row_number': row_number,
                'score': status['score'],
                'can_import': status['can_import'],
                'has_pricing': status['has_pricing'],
                'missing_required': status['missing_required'],
                'columns': cleaned_row,
            })

    candidates.sort(
        key=lambda candidate: (
            candidate['can_import'],
            candidate['has_pricing'],
            candidate['score'],
            -candidate['row_number'],
        ),
        reverse=True,
    )
    return candidates


def _csv_preview_rows(file_path, header_row=1, data_start_row=None, max_rows=5):
    try:
        df = pd.read_csv(file_path, skiprows=max(int(header_row or 1) - 1, 0), nrows=50)
    except Exception:
        return []

    data_start_row = int(data_start_row or (int(header_row or 1) + 1))
    rows_to_skip = max(data_start_row - int(header_row or 1) - 1, 0)
    if rows_to_skip:
        df = df.iloc[rows_to_skip:]

    df = df.head(max_rows).fillna("")
    return [
        {str(column): str(value) for column, value in row.items()}
        for row in df.to_dict(orient='records')
    ]


def analyze_csv_import(file_path, header_row=None, column_mapping=None, data_start_row=None):
    if header_row is None:
        candidates = _scan_csv_header_rows(file_path)
        best_candidate = candidates[0] if candidates else {'row_number': 1}
        header_row = best_candidate.get('row_number', 1)
    else:
        candidates = _scan_csv_header_rows(file_path)

    data_start_row = int(data_start_row or (int(header_row or 1) + 1))
    columns = read_csv_columns(file_path, header_row=header_row)
    status = get_import_column_status(columns, column_mapping=column_mapping)
    detected_format = detect_csv_format(file_path, header_row=header_row)
    if detected_format in {'gdax', 'coinbase_raw', 'ledger_live'}:
        status = {
            **status,
            'can_import': True,
            'has_pricing': True,
            'missing_required': [],
        }

    import_preview = {}
    normalized_rows = []
    if detected_format in {'coinbase_raw', 'ledger_live'}:
        raw_df = pd.read_csv(
            file_path,
            skiprows=max(int(header_row or 1) - 1, 0),
            dtype=str,
            keep_default_na=False,
        )
        raw_df['__gainz_source_row__'] = range(
            data_start_row,
            data_start_row + len(raw_df),
        )
        trans_df = (
            transform_coinbase_raw_to_standard(raw_df)
            if detected_format == 'coinbase_raw'
            else transform_ledger_live_to_standard(raw_df)
        )
        import_preview = summarize_standard_import_rows(
            trans_df
        )
        import_preview['source_rows'] = int(len(raw_df))
        import_preview['source_format'] = detected_format
        normalized_rows = (
            trans_df.astype(object)
            .where(pd.notna(trans_df), None)
            .to_dict(orient='records')
        )

    return {
        'can_import': status['can_import'],
        'has_pricing': status['has_pricing'],
        'detected_format': detected_format,
        'header_row': int(header_row or 1),
        'data_start_row': data_start_row,
        'columns': columns,
        'suggested_mapping': build_column_mapping_suggestions(columns),
        'mapping_fields': get_import_mapping_fields(),
        'missing_required': status['missing_required'],
        'header_candidates': candidates[:5],
        'sample_rows': _csv_preview_rows(
            file_path,
            header_row=header_row,
            data_start_row=data_start_row,
        ),
        'import_preview': import_preview,
        # Private service data. Routes never return this source-derived payload.
        '_normalized_rows': normalized_rows,
        '_source_sha256': _file_sha256(file_path),
    }


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


def _normalized_column_lookup(columns):
    return {normalize_column_name(column): column for column in columns}


def _coinbase_raw_value(row, columns, *names, default=''):
    for name in names:
        column = columns.get(normalize_column_name(name))
        if column is None:
            continue
        value = row.get(column, default)
        if not pd.isna(value):
            return value
    return default


def _coinbase_raw_leg(
    row,
    columns,
    *,
    asset,
    quantity,
    transaction_type,
    usd_total,
    economic_source,
    source_leg,
    source_quantity,
):
    asset = normalize_asset_symbol(asset)
    quantity = abs(parse_quantity_value(quantity))
    usd_total = abs(parse_money_value(usd_total))
    source_row = row.get('__gainz_source_row__')
    source_transaction_id = _coinbase_raw_value(
        row,
        columns,
        'transaction id',
        'id',
        'transaction identifier',
    )
    source_notes = _coinbase_raw_value(
        row,
        columns,
        'notes',
        'description',
        'transaction type',
    )
    warning = ''
    if transaction_type in {'Buy', 'Sell'} and not usd_total:
        warning = (
            f"Official Coinbase raw {source_leg} leg has no source-reported USD "
            f"{economic_source.lower()}. Review the source row before relying on tax totals."
        )

    return {
        'Asset Type': asset,
        'Transaction Type': transaction_type,
        'Asset Amount': quantity,
        'Date': _coinbase_raw_value(
            row,
            columns,
            'timestamp',
            'date',
            'transaction date',
            'date & time',
            'date and time',
        ),
        'Asset Price': usd_total / quantity if quantity else 0.0,
        'Gross USD': usd_total,
        'Fee USD': 0.0,
        'Source Fee Amount': None,
        'Fee Currency': 'USD',
        'Net USD': usd_total,
        'Economic Source': f"Coinbase raw {economic_source}",
        'Economic Warning': warning,
        'Source Row': source_row,
        'Source Transaction ID': source_transaction_id,
        'Source Notes': source_notes,
        'Source Quantity': str(source_quantity or '').strip(),
        'Source USD': usd_total,
        'Implied USD': usd_total,
        'Value Variance USD': 0.0,
        'Value Tolerance USD': 0.0,
        'Input Reliability': 'PASSED_SOURCE_TOTAL' if usd_total else 'NOT_CHECKED',
        'Source Leg': source_leg,
    }


def transform_coinbase_raw_to_standard(df):
    """Split Coinbase's current raw dual-leg rows without conflating either leg."""
    rows = []
    columns = _normalized_column_lookup(df.columns)

    for _, row in df.iterrows():
        raw_type = normalize_column_name(
            _coinbase_raw_value(row, columns, 'transaction type', 'type')
        )
        acquired_asset = normalize_asset_symbol(
            _coinbase_raw_value(row, columns, 'asset acquired')
        )
        acquired_quantity_source = _coinbase_raw_value(
            row,
            columns,
            'quantity acquired bought received etc',
            'quantity acquired',
        )
        acquired_quantity = parse_quantity_value(acquired_quantity_source)
        acquired_basis = parse_money_value(
            _coinbase_raw_value(
                row,
                columns,
                'cost basis incl fees and or spread usd',
                'cost basis usd',
            )
        )
        disposed_asset = normalize_asset_symbol(
            _coinbase_raw_value(row, columns, 'asset disposed sold sent etc', 'asset disposed')
        )
        disposed_quantity_source = _coinbase_raw_value(row, columns, 'quantity disposed')
        disposed_quantity = parse_quantity_value(disposed_quantity_source)
        disposed_proceeds = parse_money_value(
            _coinbase_raw_value(
                row,
                columns,
                'proceeds excl fees and or spread usd',
                'proceeds usd',
            )
        )

        has_acquired_crypto = (
            bool(acquired_asset)
            and acquired_asset not in FIAT_ASSET_SYMBOLS
            and abs(acquired_quantity) > 0
        )
        has_disposed_crypto = (
            bool(disposed_asset)
            and disposed_asset not in FIAT_ASSET_SYMBOLS
            and abs(disposed_quantity) > 0
        )

        if has_disposed_crypto:
            is_transfer = any(term in raw_type for term in ('send', 'sent', 'withdraw', 'transfer'))
            disposed_type = 'Send' if is_transfer and not abs(disposed_proceeds) else 'Sell'
            rows.append(_coinbase_raw_leg(
                row,
                columns,
                asset=disposed_asset,
                quantity=disposed_quantity,
                transaction_type=disposed_type,
                usd_total=disposed_proceeds,
                economic_source='proceeds excluding fees/spread',
                source_leg='disposed',
                source_quantity=disposed_quantity_source,
            ))

        if has_acquired_crypto:
            is_receive = any(
                term in raw_type
                for term in ('receive', 'received', 'deposit', 'reward', 'earn', 'airdrop', 'staking')
            )
            acquired_type = 'Receive' if is_receive and not abs(acquired_basis) else 'Buy'
            rows.append(_coinbase_raw_leg(
                row,
                columns,
                asset=acquired_asset,
                quantity=acquired_quantity,
                transaction_type=acquired_type,
                usd_total=acquired_basis,
                economic_source='cost basis including fees/spread',
                source_leg='acquired',
                source_quantity=acquired_quantity_source,
            ))

        if not has_disposed_crypto and not has_acquired_crypto:
            rows.append({
                'Asset Type': '',
                'Transaction Type': raw_type or 'Unsupported',
                'Asset Amount': 0,
                'Date': _coinbase_raw_value(
                    row,
                    columns,
                    'timestamp',
                    'date',
                    'transaction date',
                    'date & time',
                    'date and time',
                ),
                'Asset Price': 0,
                'Gross USD': 0,
                'Fee USD': 0,
                'Source Fee Amount': None,
                'Fee Currency': 'USD',
                'Net USD': 0,
                'Economic Source': 'Coinbase raw source row',
                'Economic Warning': '',
                'Source Row': row.get('__gainz_source_row__'),
                'Source Transaction ID': _coinbase_raw_value(
                    row,
                    columns,
                    'transaction id',
                    'id',
                    'transaction identifier',
                ),
                'Source Notes': _coinbase_raw_value(row, columns, 'notes', 'description'),
                'Source Quantity': '',
                'Source USD': None,
                'Implied USD': None,
                'Value Variance USD': None,
                'Value Tolerance USD': None,
                'Input Reliability': 'SKIPPED',
                'Source Leg': 'none',
                'Skip Reason': 'No supported crypto acquisition or disposal leg was present.',
            })

    return pd.DataFrame(rows)


def summarize_standard_import_rows(trans_df):
    if trans_df is None or trans_df.empty:
        return {
            'output_rows': 0,
            'row_counts_by_type': {},
            'quantity_totals_by_asset_and_type': {},
            'source_reported_proceeds': 0.0,
            'source_reported_basis': 0.0,
            'warning_count': 0,
            'skipped_source_rows': 0,
        }

    counts = {}
    quantities = {}
    proceeds = 0.0
    basis = 0.0
    warning_count = 0
    skipped_source_rows = 0
    for _, row in trans_df.iterrows():
        skip_reason = row.get('Skip Reason')
        if not pd.isna(skip_reason) and str(skip_reason or '').strip():
            skipped_source_rows += 1
            continue
        transaction_type = str(row.get('Transaction Type') or '')
        asset = str(row.get('Asset Type') or '')
        quantity = abs(parse_quantity_value(row.get('Asset Amount')))
        counts[transaction_type] = counts.get(transaction_type, 0) + 1
        key = f"{asset}:{transaction_type}"
        quantities[key] = quantities.get(key, 0.0) + quantity
        if transaction_type == 'Sell':
            proceeds += abs(parse_money_value(row.get('Gross USD')))
        if transaction_type == 'Buy':
            basis += abs(parse_money_value(row.get('Net USD')))
        if str(row.get('Economic Warning') or '').strip():
            warning_count += 1

    return {
        'output_rows': int(len(trans_df) - skipped_source_rows),
        'row_counts_by_type': counts,
        'quantity_totals_by_asset_and_type': quantities,
        'source_reported_proceeds': proceeds,
        'source_reported_basis': basis,
        'warning_count': warning_count,
        'skipped_source_rows': skipped_source_rows,
    }


def _optional_money_field(row, column_lookup, field):
    column = column_lookup.get(field)
    if column is None:
        return None

    value = row.get(column)
    if pd.isna(value) or str(value).strip().lower() in {'', 'nan', 'none'}:
        return None

    return abs(parse_money_value(value))


def _append_warning(existing, message):
    existing = str(existing or '').strip()
    message = str(message or '').strip()
    if not existing:
        return message
    if not message:
        return existing
    return f"{existing} {message}"


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source_file:
        for chunk in iter(lambda: source_file.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _value_consistency_check(source_usd, implied_usd):
    if source_usd in (None, 0) or implied_usd in (None, 0):
        return {
            'status': 'NOT_CHECKED',
            'variance': None,
            'tolerance': None,
            'warning': '',
        }

    source_usd = abs(float(source_usd))
    implied_usd = abs(float(implied_usd))
    variance = abs(implied_usd - source_usd)
    # A 10%/$1 tolerance accommodates ordinary spread and rounding while still
    # stopping unit/exponent errors before they enter basis calculations.
    tolerance = max(1.0, source_usd * 0.10)
    if variance <= tolerance:
        return {
            'status': 'PASSED',
            'variance': variance,
            'tolerance': tolerance,
            'warning': '',
        }

    warning = (
        f"{INPUT_RELIABILITY_BLOCKER_PREFIX} source USD value ${source_usd:,.2f} "
        f"does not agree with quantity x unit price (${implied_usd:,.2f}); "
        f"variance ${variance:,.2f} exceeds the ${tolerance:,.2f} tolerance. "
        "Correct the source mapping before relying on FIFO or tax totals."
    )
    return {
        'status': 'BLOCKING',
        'variance': variance,
        'tolerance': tolerance,
        'warning': warning,
    }


def _standard_economics(row, column_lookup, quantity, transaction_type, profile='generic'):
    transaction_type = standardize_transaction_type(transaction_type)
    direct_price = abs(parse_money_value(get_row_value(row, column_lookup, 'asset_price')))
    subtotal = _optional_money_field(row, column_lookup, 'subtotal')
    total = _optional_money_field(row, column_lookup, 'total')
    net_amount = _optional_money_field(row, column_lookup, 'net_amount')
    fiat_amount = _optional_money_field(row, column_lookup, 'fiat_amount')
    source_fee_amount = _optional_money_field(row, column_lookup, 'fee')
    fee_currency = normalize_asset_symbol(
        get_row_value(
            row,
            column_lookup,
            'fee_currency',
            get_row_value(row, column_lookup, 'price_currency', 'USD'),
        )
    ) or 'USD'
    fee_is_usd = fee_currency in FIAT_ASSET_SYMBOLS
    fee_usd = source_fee_amount if fee_is_usd else None

    gross = None
    net = None
    source_parts = []

    if profile == 'coinbase':
        gross = subtotal
        net = total
        source_parts.extend(field for field, value in (('subtotal', subtotal), ('total', total)) if value is not None)
    elif profile == 'cashapp':
        gross = fiat_amount
        net = net_amount
        source_parts.extend(field for field, value in (('amount', fiat_amount), ('net amount', net_amount)) if value is not None)
    else:
        gross = subtotal if subtotal is not None else fiat_amount
        net = net_amount if net_amount is not None else total
        source_parts.extend(field for field, value in (
            ('subtotal', subtotal),
            ('gross value', fiat_amount),
            ('net amount', net_amount),
            ('total', total),
        ) if value is not None)

    spot_gross = direct_price * abs(quantity) if direct_price and quantity else None
    if gross is None:
        gross = spot_gross
        if gross is not None:
            source_parts.append('spot price')

    if gross is None and net is not None:
        if transaction_type == 'Buy' and fee_usd is not None:
            gross = max(net - fee_usd, 0.0)
        elif transaction_type == 'Sell' and fee_usd is not None:
            gross = net + fee_usd
        else:
            gross = net

    if gross is None:
        gross = 0.0

    if net is None:
        if transaction_type == 'Buy':
            net = gross + float(fee_usd or 0.0)
        elif transaction_type == 'Sell':
            net = max(gross - float(fee_usd or 0.0), 0.0)
        else:
            net = gross

    warning = ''
    if source_fee_amount and not fee_is_usd:
        warning = (
            f"Fee amount {source_fee_amount:g} {fee_currency} was preserved but not converted to USD. "
            "Add a supported USD fee value before relying on tax totals."
        )
    elif (
        source_fee_amount is not None
        and transaction_type in {'Buy', 'Sell'}
        and not (profile == 'coinbase' and total is not None)
    ):
        expected_net = gross + source_fee_amount if transaction_type == 'Buy' else max(gross - source_fee_amount, 0.0)
        if abs(net - expected_net) > 0.02:
            warning = (
                f"Source gross, fee, and net values differ by ${abs(net - expected_net):,.2f}. "
                "Review the source economics before relying on tax totals."
            )

    asset_price = direct_price or (gross / abs(quantity) if quantity else 0.0)
    implied_usd = direct_price * abs(quantity) if direct_price and quantity else None
    consistency_target = gross
    if profile == 'cashapp' and transaction_type in {'Send', 'Receive'} and net is not None:
        consistency_target = net
        source_parts.append('net value used for wallet-movement integrity check')
    consistency = _value_consistency_check(consistency_target, implied_usd)
    warning = _append_warning(warning, consistency['warning'])
    if profile == 'coinbase' and total is not None:
        source_parts.append('Coinbase total inclusive of fees/spread used as tax value')
    return {
        'Asset Price': asset_price,
        'Gross USD': gross,
        'Fee USD': fee_usd,
        'Source Fee Amount': source_fee_amount,
        'Fee Currency': fee_currency,
        'Net USD': net,
        'Economic Source': ', '.join(dict.fromkeys(source_parts)) or 'spot price',
        'Economic Warning': warning,
        'Source USD': consistency_target,
        'Implied USD': implied_usd,
        'Value Variance USD': consistency['variance'],
        'Value Tolerance USD': consistency['tolerance'],
        'Input Reliability': consistency['status'],
    }


def _standard_row_from_lookup(row, column_lookup, profile='generic'):
    quantity = parse_quantity_value(get_row_value(row, column_lookup, 'asset_amount'))
    transaction_type = standardize_transaction_type(get_row_value(row, column_lookup, 'transaction_type', ''))
    economics = _standard_economics(
        row,
        column_lookup,
        quantity,
        transaction_type,
        profile=profile,
    )

    standard_row = {
        'Asset Type': normalize_asset_symbol(get_row_value(row, column_lookup, 'asset_type')),
        'Transaction Type': transaction_type,
        'Asset Amount': abs(quantity) if quantity < 0 else quantity,
        'Date': get_row_value(row, column_lookup, 'date'),
        'Source Row': row.get('__gainz_source_row__'),
        'Source Transaction ID': get_row_value(row, column_lookup, 'transaction_id', ''),
        'Source Notes': get_row_value(row, column_lookup, 'notes', ''),
        'Source Quantity': str(get_row_value(row, column_lookup, 'asset_amount', '') or '').strip(),
    }
    standard_row.update(economics)
    return standard_row


def transform_generic_to_standard(df, column_mapping=None):
    column_lookup = build_column_lookup(df.columns, column_mapping=column_mapping)
    required_fields = {'date', 'transaction_type', 'asset_type', 'asset_amount'}

    if not required_fields.issubset(column_lookup):
        return df

    result_df = pd.DataFrame([
        _standard_row_from_lookup(row, column_lookup, profile='generic')
        for _, row in df.iterrows()
    ])
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


def detect_csv_format(file_path, header_row=1):
    """
    Detects the CSV format by examining the header row.
    
    Args:
        file_path (str): Path to the CSV file
        
    Returns:
        str: 'cashapp', 'coinbase', or 'unknown'
    """
    try:
        header = read_csv_columns(file_path, header_row=header_row)
        column_lookup = build_column_lookup(header)
        normalized_headers = {normalize_column_name(header_name) for header_name in header}
        filename_hint = normalize_column_name(os.path.basename(file_path))

        if COINBASE_RAW_COLUMNS.issubset(normalized_headers):
            return 'coinbase_raw'

        if LEDGER_LIVE_COLUMNS.issubset(normalized_headers):
            return 'ledger_live'

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

        gdax_markers = {'trade id', 'size unit', 'price fee total unit', 'product'}
        gdax_match = sum(1 for field in common_fields if field in column_lookup)
        gdax_match += sum(1 for marker in gdax_markers if marker in normalized_headers)

        if 'cash app' in filename_hint or 'cashapp' in filename_hint:
            cash_app_match += 2
        if 'coinbase' in filename_hint:
            coinbase_match += 2
        if 'gdax' in filename_hint:
            gdax_match += 2

        if cash_app_match >= 6 and cash_app_match >= coinbase_match and cash_app_match >= gdax_match:
            return 'cashapp'
        elif coinbase_match >= 6 and coinbase_match >= gdax_match:
            return 'coinbase'
        elif gdax_match >= 5:
            return 'gdax'
        else:
            return 'unknown'
    except Exception:
        parsers_logger.exception("Could not detect CSV format for %s.", os.path.basename(file_path))
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
    result_df = pd.DataFrame([
        _standard_row_from_lookup(row, column_lookup, profile='cashapp')
        for _, row in df.iterrows()
    ])

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
        standard_row = _standard_row_from_lookup(row, column_lookup, profile='coinbase')
        asset_price = standard_row['Asset Price']

        if 'convert' in trans_type_lower:
            convert = parse_coinbase_convert_note(get_row_value(row, column_lookup, 'notes'))
            if convert:
                conversion_gross = (
                    abs(parse_money_value(get_row_value(row, column_lookup, 'subtotal')))
                    or (convert['from_quantity'] * asset_price)
                    or abs(parse_money_value(get_row_value(row, column_lookup, 'total')))
                )
                conversion_net = (
                    abs(parse_money_value(get_row_value(row, column_lookup, 'total')))
                    or conversion_gross
                )
                conversion_fee = abs(parse_money_value(get_row_value(row, column_lookup, 'fee')))

                sell_spot = conversion_gross / convert['from_quantity'] if convert['from_quantity'] else asset_price
                buy_spot = conversion_gross / convert['to_quantity'] if convert['to_quantity'] else 0.0
                conversion_warning = (
                    "Coinbase Convert fee was preserved on the disposal side only; review the source "
                    "before relying on acquired-asset basis."
                    if conversion_fee
                    else ''
                )

                rows.append({
                    'Asset Type': convert['from_asset'],
                    'Transaction Type': 'Sell',
                    'Asset Amount': abs(convert['from_quantity']),
                    'Date': timestamp,
                    'Asset Price': sell_spot,
                    'Gross USD': conversion_gross,
                    'Fee USD': conversion_fee,
                    'Source Fee Amount': conversion_fee,
                    'Fee Currency': standard_row['Fee Currency'],
                    'Net USD': conversion_net,
                    'Economic Source': standard_row['Economic Source'],
                    'Economic Warning': '',
                    'Source Row': standard_row['Source Row'],
                    'Source Transaction ID': standard_row['Source Transaction ID'],
                    'Source Notes': standard_row['Source Notes'],
                })
                rows.append({
                    'Asset Type': convert['to_asset'],
                    'Transaction Type': 'Buy',
                    'Asset Amount': abs(convert['to_quantity']),
                    'Date': timestamp,
                    'Asset Price': buy_spot,
                    'Gross USD': conversion_gross,
                    'Fee USD': 0.0,
                    'Source Fee Amount': 0.0,
                    'Fee Currency': standard_row['Fee Currency'],
                    'Net USD': conversion_gross,
                    'Economic Source': standard_row['Economic Source'],
                    'Economic Warning': conversion_warning,
                    'Source Row': standard_row['Source Row'],
                    'Source Transaction ID': standard_row['Source Transaction ID'],
                    'Source Notes': standard_row['Source Notes'],
                })
                continue

        standard_type = standardize_transaction_type(trans_type)

        if pd.isna(asset) or asset == '' or asset in FIAT_ASSET_SYMBOLS:
            continue

        if standard_type in ('Sell', 'Send') or quantity < 0:
            quantity = abs(quantity)

        standard_row.update({
            'Asset Type': asset,
            'Transaction Type': standard_type,
            'Asset Amount': quantity,
            'Date': timestamp,
            'Asset Price': asset_price,
        })
        rows.append(standard_row)

    return pd.DataFrame(rows)


def transform_gdax_to_standard(df):
    """
    Transforms GDAX CSV format to the standard format expected by import_transactions.
    """
    rows = []

    for _, row in df.iterrows():
        product = str(row.get('product', '')).upper()
        if not product or '-' not in product:
            continue

        asset = product.split('-')[0]

        side = str(row.get('side', '')).upper()
        if side == 'BUY':
            trans_type = 'Buy'
        elif side == 'SELL':
            trans_type = 'Sell'
        else:
            trans_type = standardize_transaction_type(side)

        timestamp = row.get('created at')
        quantity = parse_quantity_value(row.get('size'))
        asset_price = parse_money_value(row.get('price'))
        gross = abs(parse_money_value(row.get('total'))) or (abs(quantity) * asset_price)
        source_fee_amount = abs(parse_money_value(row.get('fee')))
        fee_currency = normalize_asset_symbol(row.get('price/fee/total unit', 'USD')) or 'USD'
        fee_usd = source_fee_amount if fee_currency in FIAT_ASSET_SYMBOLS else None
        net = (
            gross + float(fee_usd or 0.0)
            if trans_type == 'Buy'
            else max(gross - float(fee_usd or 0.0), 0.0)
        )
        economics_warning = ''
        if source_fee_amount and fee_usd is None:
            economics_warning = (
                f"Fee amount {source_fee_amount:g} {fee_currency} was preserved but not converted to USD. "
                "Add a supported USD fee value before relying on tax totals."
            )

        rows.append({
            'Asset Type': asset,
            'Transaction Type': trans_type,
            'Asset Amount': abs(quantity),
            'Date': timestamp,
            'Asset Price': asset_price,
            'Gross USD': gross,
            'Fee USD': fee_usd,
            'Source Fee Amount': source_fee_amount,
            'Fee Currency': fee_currency,
            'Net USD': net,
            'Economic Source': 'GDAX total, fee, and price',
            'Economic Warning': economics_warning,
            'Source Row': row.get('__gainz_source_row__'),
            'Source Transaction ID': row.get('trade id', ''),
            'Source Notes': '',
        })

    return pd.DataFrame(rows)


def transform_ledger_live_to_standard(df):
    """Normalize Ledger Live wallet movements without inventing USD economics."""
    rows = []
    columns = _normalized_column_lookup(df.columns)

    for _, row in df.iterrows():
        operation_type = normalize_column_name(
            _coinbase_raw_value(row, columns, 'operation type')
        ).upper()
        transaction_type = {'IN': 'Receive', 'OUT': 'Send'}.get(operation_type)
        source_row = row.get('__gainz_source_row__')
        if transaction_type is None:
            rows.append({
                'Asset Type': normalize_asset_symbol(
                    _coinbase_raw_value(row, columns, 'currency ticker')
                ),
                'Transaction Type': operation_type or 'Unsupported',
                'Asset Amount': 0,
                'Date': _coinbase_raw_value(row, columns, 'operation date'),
                'Asset Price': 0,
                'Gross USD': 0,
                'Fee USD': None,
                'Source Fee Amount': None,
                'Fee Currency': '',
                'Net USD': 0,
                'Economic Source': 'Ledger Live wallet movement',
                'Economic Warning': '',
                'Source Row': source_row,
                'Source Transaction ID': _coinbase_raw_value(row, columns, 'operation hash'),
                'Source Notes': _coinbase_raw_value(row, columns, 'account name'),
                'Source Quantity': '',
                'Source USD': None,
                'Implied USD': None,
                'Value Variance USD': None,
                'Value Tolerance USD': None,
                'Input Reliability': 'SKIPPED',
                'Source Leg': 'wallet_movement',
                'Skip Reason': f"Unsupported Ledger Live operation type '{operation_type or 'blank'}'.",
            })
            continue

        asset = normalize_asset_symbol(
            _coinbase_raw_value(row, columns, 'currency ticker')
        )
        source_quantity = _coinbase_raw_value(row, columns, 'operation amount')
        source_fee = _coinbase_raw_value(row, columns, 'operation fees')
        fee_quantity = abs(parse_quantity_value(source_fee))
        rows.append({
            'Asset Type': asset,
            'Transaction Type': transaction_type,
            'Asset Amount': abs(parse_quantity_value(source_quantity)),
            'Date': _coinbase_raw_value(row, columns, 'operation date'),
            'Asset Price': 0,
            'Gross USD': 0,
            'Fee USD': None,
            'Source Fee Amount': fee_quantity if fee_quantity else None,
            'Fee Currency': asset,
            'Net USD': 0,
            'Economic Source': 'Ledger Live wallet movement; no USD value inferred',
            'Economic Warning': '',
            'Source Row': source_row,
            'Source Transaction ID': _coinbase_raw_value(row, columns, 'operation hash'),
            'Source Notes': _coinbase_raw_value(row, columns, 'account name'),
            'Source Quantity': str(source_quantity or '').strip(),
            'Source USD': None,
            'Implied USD': None,
            'Value Variance USD': None,
            'Value Tolerance USD': None,
            'Input Reliability': 'PASSED_WALLET_MOVEMENT',
            'Source Leg': 'wallet_movement',
        })

    return pd.DataFrame(rows)

def import_transactions(
    file_path,
    transactions,
    header_row=1,
    column_mapping=None,
    data_start_row=None,
    prepared_rows=None,
    prepared_format=None,
):
    """
    Imports transactions from a given file path and adds them to the Transactions object.
    Prevents duplicate imports by checking for existing transactions with the same attributes.
    Now handles multiple CSV formats automatically.

    Args:
        file_path (str): The path to the file containing transaction data.
        transactions (Transactions): The Transactions object to update.
        header_row (int): 1-based row number containing CSV headers.
        column_mapping (dict): Optional canonical field to CSV column mapping.
        data_start_row (int): 1-based row number where data begins. Defaults to the row after headers.

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
        import_warnings = []

        # Detect the CSV format unless a previously reviewed immutable payload is used.
        csv_format = prepared_format or detect_csv_format(file_path, header_row=header_row)
        parsers_logger.info("Detected CSV format: %s", csv_format)

        # Read the CSV file
        header_row = int(header_row or 1)
        data_start_row = int(data_start_row or (header_row + 1))
        # Keep the source cell text intact. In particular, pandas must not turn a
        # small decimal quantity into a float whose string form loses the source
        # representation used by the import receipt.
        if prepared_rows is not None:
            trans_df = pd.DataFrame(prepared_rows)
        else:
            raw_df = pd.read_csv(
                file_path,
                skiprows=max(header_row - 1, 0),
                dtype=str,
                keep_default_na=False,
            )
            rows_to_skip = max(data_start_row - header_row - 1, 0)
            if rows_to_skip:
                raw_df = raw_df.iloc[rows_to_skip:].reset_index(drop=True)
            raw_df['__gainz_source_row__'] = range(data_start_row, data_start_row + len(raw_df))

            # Transform to standard format based on detected format
            if column_mapping:
                trans_df = transform_generic_to_standard(raw_df, column_mapping=column_mapping)
            elif csv_format == 'cashapp':
                trans_df = transform_cashapp_to_standard(raw_df)
            elif csv_format == 'coinbase':
                trans_df = transform_coinbase_to_standard(raw_df)
            elif csv_format == 'coinbase_raw':
                trans_df = transform_coinbase_raw_to_standard(raw_df)
            elif csv_format == 'ledger_live':
                trans_df = transform_ledger_live_to_standard(raw_df)
            elif csv_format == 'gdax':
                trans_df = transform_gdax_to_standard(raw_df)
            else:
                trans_df = transform_generic_to_standard(raw_df)
                if trans_df is raw_df:
                    print("Warning: Unknown CSV format. Attempting to process as-is.")

        missing_standard_columns = STANDARD_IMPORT_COLUMNS - set(trans_df.columns)
        if missing_standard_columns:
            warning = (
                f"Could not identify required columns in {os.path.basename(file_path)}. "
                "Use the import column mapper to choose Date/time, Transaction type, "
                "Asset symbol, Asset quantity, and a USD spot price or total USD value."
            )
            print(f"Warning: {warning}")
            import_warnings.append(warning)
            existing_warnings = getattr(transactions, 'import_warnings', [])
            transactions.import_warnings = existing_warnings + import_warnings
            transactions.last_import_result = {
                "file_path": file_path,
                "imported_count": 0,
                "skipped_count": 0,
                "warnings": import_warnings,
            }
            return (0, 0)

        transactions_added = False
        imported_count = 0
        skipped_count = 0
        skipped_rows = []
        integrity_checks = []

        for row_number, (_, row) in enumerate(trans_df.iterrows(), start=data_start_row):
            try:
                source_row_number = row.get('Source Row', row_number)
                if pd.isna(source_row_number):
                    source_row_number = row_number
                source_row_number = int(source_row_number)
                raw_skip_reason = row.get('Skip Reason', '')
                explicit_skip_reason = (
                    '' if pd.isna(raw_skip_reason) else str(raw_skip_reason or '').strip()
                )
                if explicit_skip_reason:
                    warning = (
                        f"Skipped row {source_row_number} from {os.path.basename(file_path)}: "
                        f"{explicit_skip_reason}"
                    )
                    import_warnings.append(warning)
                    skipped_count += 1
                    skipped_rows.append({
                        'source_row': source_row_number,
                        'source_transaction_id': str(row.get('Source Transaction ID', '') or ''),
                        'transaction_type': str(row.get('Transaction Type', '') or ''),
                        'asset': str(row.get('Asset Type', '') or ''),
                        'reason': explicit_skip_reason,
                        'affects_calculations': False,
                    })
                    continue
                symbol = normalize_asset_symbol(row['Asset Type'])
                if not symbol or symbol in FIAT_ASSET_SYMBOLS:
                    warning = (
                        f"Skipped row {source_row_number} from {os.path.basename(file_path)}: "
                        f"missing or non-crypto asset '{row['Asset Type']}'"
                    )
                    print(f"Warning: {warning}")
                    import_warnings.append(warning)
                    skipped_count += 1
                    skipped_rows.append({
                        'source_row': source_row_number,
                        'source_transaction_id': str(row.get('Source Transaction ID', '') or ''),
                        'transaction_type': str(row.get('Transaction Type', '') or ''),
                        'asset': str(row.get('Asset Type', '') or ''),
                        'reason': 'Missing or non-crypto asset.',
                        'affects_calculations': False,
                    })
                    continue

                quantity = parse_quantity_value(row['Asset Amount'])
                time_stamp = parse_gainz_datetime(row['Date'])
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
                        f"Skipped row {source_row_number} from {os.path.basename(file_path)}: "
                        f"unrecognized transaction type '{row['Transaction Type']}'"
                    )
                    print(f"Warning: {warning}")
                    import_warnings.append(warning)
                    skipped_count += 1
                    skipped_rows.append({
                        'source_row': source_row_number,
                        'source_transaction_id': str(row.get('Source Transaction ID', '') or ''),
                        'transaction_type': str(row.get('Transaction Type', '') or ''),
                        'asset': symbol,
                        'reason': f"Unrecognized transaction type: {row['Transaction Type']}",
                        'affects_calculations': True,
                    })
                    continue

                temp_trans.set_economics(
                    fee=None if pd.isna(row.get('Fee USD')) else row.get('Fee USD'),
                    gross_usd_total=None if pd.isna(row.get('Gross USD')) else row.get('Gross USD'),
                    net_usd_total=None if pd.isna(row.get('Net USD')) else row.get('Net USD'),
                    fee_currency=row.get('Fee Currency', 'USD'),
                    source_fee_amount=(
                        None if pd.isna(row.get('Source Fee Amount')) else row.get('Source Fee Amount')
                    ),
                    source_row=source_row_number,
                    source_transaction_id=row.get('Source Transaction ID', ''),
                    economics_source=row.get('Economic Source', ''),
                    economics_warning=row.get('Economic Warning', ''),
                    source_notes=row.get('Source Notes', ''),
                    source_quantity_text=row.get('Source Quantity', ''),
                    source_usd_total=(
                        None if pd.isna(row.get('Source USD')) else row.get('Source USD')
                    ),
                    implied_usd_total=(
                        None if pd.isna(row.get('Implied USD')) else row.get('Implied USD')
                    ),
                    value_variance_usd=(
                        None if pd.isna(row.get('Value Variance USD')) else row.get('Value Variance USD')
                    ),
                    value_tolerance_usd=(
                        None if pd.isna(row.get('Value Tolerance USD')) else row.get('Value Tolerance USD')
                    ),
                    input_reliability_status=row.get('Input Reliability', 'NOT_CHECKED'),
                    source_leg=row.get('Source Leg', ''),
                )

                integrity_check = {
                    'source_row': source_row_number,
                    'source_transaction_id': temp_trans.source_transaction_id,
                    'asset': symbol,
                    'transaction_type': temp_trans.trans_type,
                    'source_quantity': temp_trans.source_quantity_text,
                    'interpreted_quantity': quantity,
                    'source_usd': temp_trans.source_usd_total,
                    'implied_usd': temp_trans.implied_usd_total,
                    'variance_usd': temp_trans.value_variance_usd,
                    'tolerance_usd': temp_trans.value_tolerance_usd,
                    'status': temp_trans.input_reliability_status,
                    'outcome': 'Pending',
                }
                integrity_checks.append(integrity_check)

                if temp_trans.economics_warning:
                    import_warnings.append(
                        f"Imported row {source_row_number} from {os.path.basename(file_path)} with an economic-value warning: "
                        f"{temp_trans.economics_warning}"
                    )

                if usd_spot == 0 and temp_trans.trans_type in {'buy', 'sell'}:
                    import_warnings.append(
                        f"Imported row {source_row_number} from {os.path.basename(file_path)} with $0 USD spot price. "
                        "Map a USD spot price or total USD value column if this is not intentional."
                    )

                # Check for duplicates before adding
                if is_duplicate(temp_trans, transactions.transactions):
                    # Use logger instead of print
                    import logging
                    logger = logging.getLogger('parsers')
                    logger.info(f"Skipping duplicate transaction: {symbol} {quantity} {time_stamp}")
                    skipped_count += 1
                    skipped_rows.append({
                        'source_row': source_row_number,
                        'source_transaction_id': temp_trans.source_transaction_id,
                        'transaction_type': temp_trans.trans_type,
                        'asset': symbol,
                        'reason': 'Duplicate or companion-source activity already imported.',
                        'affects_calculations': False,
                    })
                    integrity_check['outcome'] = 'Skipped'
                else:
                    transactions.transactions.append(temp_trans)
                    transactions_added = True
                    imported_count += 1
                    integrity_check['outcome'] = 'Imported'
            except KeyError:
                warning = (
                    f"Skipped row {source_row_number if 'source_row_number' in locals() else row_number} from {os.path.basename(file_path)}: "
                    "missing one of the required import columns."
                )
                parsers_logger.exception("Import row is missing a required column.")
                import_warnings.append(warning)
                skipped_count += 1
                skipped_rows.append({
                    'source_row': source_row_number if 'source_row_number' in locals() else row_number,
                    'source_transaction_id': '',
                    'transaction_type': '',
                    'asset': '',
                    'reason': 'Missing one of the required import columns.',
                    'affects_calculations': True,
                })
                continue
            except Exception:
                warning = (
                    f"Skipped row {source_row_number if 'source_row_number' in locals() else row_number} from {os.path.basename(file_path)}: "
                    "Gainz could not parse this row. Check date, transaction type, "
                    "asset quantity, and USD value."
                )
                parsers_logger.exception("Import row could not be parsed.")
                import_warnings.append(warning)
                skipped_count += 1
                skipped_rows.append({
                    'source_row': source_row_number if 'source_row_number' in locals() else row_number,
                    'source_transaction_id': '',
                    'transaction_type': '',
                    'asset': '',
                    'reason': 'Could not parse date, transaction type, asset quantity, or USD value.',
                    'affects_calculations': True,
                })
                continue

        existing_warnings = getattr(transactions, 'import_warnings', [])
        transactions.import_warnings = existing_warnings + import_warnings
        source_hash = _file_sha256(file_path)
        import_receipts = []
        for check in integrity_checks:
            if check.get('outcome') != 'Imported':
                continue
            import_receipts.append({
                'source': file_path,
                'source_sha256': source_hash,
                'source_row': check.get('source_row'),
                'source_transaction_id': check.get('source_transaction_id', ''),
                'original_type': check.get('transaction_type', ''),
                'asset': check.get('asset', ''),
                'source_quantity': check.get('source_quantity', ''),
                'interpreted_quantity': check.get('interpreted_quantity', ''),
                'outcome': 'Imported',
                'reason': (
                    'Input reliability check failed; downstream tax totals are suppressed.'
                    if check.get('status') == 'BLOCKING'
                    else 'Imported and retained for calculations.'
                ),
                'affects_calculations': True,
                'input_reliability_status': check.get('status', ''),
            })
        for skipped in skipped_rows:
            import_receipts.append({
                'source': file_path,
                'source_sha256': source_hash,
                'source_row': skipped.get('source_row'),
                'source_transaction_id': skipped.get('source_transaction_id', ''),
                'original_type': skipped.get('transaction_type', ''),
                'asset': skipped.get('asset', ''),
                'source_quantity': '',
                'interpreted_quantity': '',
                'outcome': 'Skipped',
                'reason': skipped.get('reason', ''),
                'affects_calculations': bool(skipped.get('affects_calculations')),
                'input_reliability_status': 'SKIPPED',
            })
        existing_receipts = [
            receipt
            for receipt in getattr(transactions, 'import_receipts', []) or []
            if str(receipt.get('source') or '') != str(file_path)
        ]
        transactions.import_receipts = existing_receipts + import_receipts

        transactions.last_import_result = {
            "file_path": file_path,
            "imported_count": imported_count,
            "skipped_count": skipped_count,
            "warnings": import_warnings,
            "skipped_rows": skipped_rows,
            "integrity_checks": integrity_checks,
            "import_receipts": import_receipts,
            "input_reliability_failed": any(
                row.get('status') == 'BLOCKING' for row in integrity_checks
            ),
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
            
    except Exception:
        parsers_logger.exception("Could not import transactions from %s.", os.path.basename(file_path))
        warning = (
            f"Could not import {os.path.basename(file_path)}. Check that the file is a "
            "readable CSV and use the column mapper if the headers are unusual."
        )
        existing_warnings = getattr(transactions, 'import_warnings', [])
        transactions.import_warnings = existing_warnings + [warning]
        transactions.last_import_result = {
            "file_path": file_path,
            "imported_count": 0,
            "skipped_count": 0,
            "warnings": [warning],
        }
        return (0, 0)
