#!/usr/bin/env python
"""
Script to analyze Bitcoin sell transactions by year between two save files.
"""
import pandas as pd
import os
from datetime import datetime

# Define the files to analyze
OLD_FILE = "saves/saved_Y2024-M04-D01_H18-M47-S46.xlsx"
NEW_FILE = "saves/saved_Y2025-M04-D12_H09-M36-S15.xlsx"

def analyze_btc_by_year():
    """Analyze BTC sell transactions by year in both files."""
    print(f"Analyzing Bitcoin transactions by year\n")
    print(f"Old file: {OLD_FILE}")
    print(f"New file: {NEW_FILE}\n")
    
    # Load data
    try:
        old_df = pd.read_excel(OLD_FILE, sheet_name="All Transactions")
        new_df = pd.read_excel(NEW_FILE, sheet_name="All Transactions")
        
        print(f"Successfully loaded both files")
        print(f"Old file contains {len(old_df)} transactions")
        print(f"New file contains {len(new_df)} transactions")
        
        # Check column names to ensure we're using the right ones
        print(f"\nOld file columns: {', '.join(old_df.columns)}")
    except Exception as e:
        print(f"Error loading files: {e}")
        return

    # Focus on BTC transactions
    old_btc = old_df[old_df['symbol'] == 'BTC'].copy()  # Use .copy() to avoid the SettingWithCopyWarning
    new_btc = new_df[new_df['symbol'] == 'BTC'].copy()
    
    print(f"\n===== ALL BTC TRANSACTIONS =====")
    print(f"Old file: {len(old_btc)} BTC transactions")
    print(f"New file: {len(new_btc)} BTC transactions")
    
    # Convert timestamps and add year column
    old_btc['timestamp'] = pd.to_datetime(old_btc['time_stamp'], errors='coerce')
    new_btc['timestamp'] = pd.to_datetime(new_btc['time_stamp'], errors='coerce')
    
    old_btc['year'] = old_btc['timestamp'].dt.year
    new_btc['year'] = new_btc['timestamp'].dt.year
    
    # Group by year and transaction type for quantity sum and count
    print("\n===== OLD FILE BTC TRANSACTIONS BY YEAR =====")
    old_summary = old_btc.groupby(['year', 'trans_type']).agg({
        'quantity': ['sum', 'count']
    })
    print(old_summary)
    
    print("\n===== NEW FILE BTC TRANSACTIONS BY YEAR =====")
    new_summary = new_btc.groupby(['year', 'trans_type']).agg({
        'quantity': ['sum', 'count']
    })
    print(new_summary)
    
    # Focus specifically on 2023 sells
    old_2023_sells = old_btc[(old_btc['year'] == 2023) & (old_btc['trans_type'] == 'sell')]
    new_2023_sells = new_btc[(new_btc['year'] == 2023) & (new_btc['trans_type'] == 'sell')]
    
    print("\n===== 2023 BTC SELL TRANSACTIONS =====")
    print(f"Old file: {len(old_2023_sells)} sell transactions in 2023, total {old_2023_sells['quantity'].sum():.8f} BTC")
    print(f"New file: {len(new_2023_sells)} sell transactions in 2023, total {new_2023_sells['quantity'].sum():.8f} BTC")
    print(f"Difference: {len(new_2023_sells) - len(old_2023_sells)} transactions, {new_2023_sells['quantity'].sum() - old_2023_sells['quantity'].sum():.8f} BTC")
    
    # Let's look at the actual new 2023 sell transactions
    print("\n===== NEW 2023 SELL TRANSACTIONS DETAILS =====")
    for i, (idx, row) in enumerate(new_2023_sells.iterrows()):
        print(f"{i+1}. {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | {row['quantity']:.8f} BTC | ${row['usd_spot']:.2f} | Source: {row['source']}")
    
    # Convert old and new sells to sets for easy comparison
    old_sells_set = set()
    for idx, row in old_2023_sells.iterrows():
        # Create a tuple of timestamp (date only), quantity (rounded), and price (rounded)
        old_sells_set.add((
            row['timestamp'].strftime('%Y-%m-%d'), 
            round(row['quantity'], 8), 
            round(row['usd_spot'], 2)
        ))
    
    # Find which 2023 sell transactions in new file aren't in old file
    new_transactions = []
    for idx, row in new_2023_sells.iterrows():
        trans_tuple = (
            row['timestamp'].strftime('%Y-%m-%d'),
            round(row['quantity'], 8),
            round(row['usd_spot'], 2)
        )
        if trans_tuple not in old_sells_set:
            new_transactions.append((
                row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                row['quantity'],
                row['usd_spot'],
                row['source']
            ))
    
    print(f"\n===== NEW TRANSACTIONS ADDED TO 2023 =====")
    print(f"Found {len(new_transactions)} new transactions in 2023 that weren't in the old file:")
    for i, (date, qty, price, source) in enumerate(new_transactions):
        print(f"{i+1}. {date} | {qty:.8f} BTC | ${price:.2f} | Source: {source}")
    
    # Check for duplicates within the new file (by date + quantity)
    new_2023_sells['date'] = new_2023_sells['timestamp'].dt.strftime('%Y-%m-%d')
    duplicates = new_2023_sells[new_2023_sells.duplicated(['date', 'quantity', 'usd_spot'], keep=False)]
    
    print(f"\n===== POTENTIAL DUPLICATES IN 2023 SELLS =====")
    if len(duplicates) > 0:
        duplicates = duplicates.sort_values(['date', 'quantity'])
        print(f"Found {len(duplicates)} potential duplicate records:")
        for i, (idx, row) in enumerate(duplicates.iterrows()):
            print(f"{i+1}. {row['timestamp']} | {row['quantity']:.8f} BTC | ${row['usd_spot']:.2f} | Source: {row['source']}")
    else:
        print("No duplicates found in the new file's 2023 sell transactions.")

if __name__ == "__main__":
    analyze_btc_by_year()
