#!/usr/bin/env python
"""
Script to analyze Bitcoin sell transactions and identify duplicates.
"""
import pandas as pd
import os
from datetime import datetime
import sys

# Define the files to analyze
OLD_FILE = "saves/saved_Y2024-M04-D01_H18-M47-S46.xlsx"
NEW_FILE = "saves/saved_Y2025-M04-D12_H09-M23-S17.xlsx"

def analyze_btc_sells():
    """Analyze BTC sell transactions in both files and identify duplicates."""
    print(f"Analyzing Bitcoin sell transactions\n")
    print(f"Old file: {OLD_FILE}")
    print(f"New file: {NEW_FILE}\n")
    
    # Load data
    try:
        old_df = pd.read_excel(OLD_FILE, sheet_name="All Transactions")
        new_df = pd.read_excel(NEW_FILE, sheet_name="All Transactions")
        
        print(f"Successfully loaded both files")
        print(f"Old file contains {len(old_df)} transactions")
        print(f"New file contains {len(new_df)} transactions")
    except Exception as e:
        print(f"Error loading files: {e}")
        return
    
    # Focus on BTC sell transactions
    old_btc_sells = old_df[(old_df['symbol'] == 'BTC') & (old_df['trans_type'] == 'sell')]
    new_btc_sells = new_df[(new_df['symbol'] == 'BTC') & (new_df['trans_type'] == 'sell')]
    
    print(f"\n===== BTC SELL SUMMARY =====")
    print(f"Old file: {len(old_btc_sells)} BTC sell transactions")
    print(f"New file: {len(new_btc_sells)} BTC sell transactions")
    print(f"Difference: {len(new_btc_sells) - len(old_btc_sells)} transactions")
    
    # Calculate total BTC sold
    old_total = old_btc_sells['quantity'].sum()
    new_total = new_btc_sells['quantity'].sum()
    
    print(f"\nOld file total BTC sold: {old_total:.8f}")
    print(f"New file total BTC sold: {new_total:.8f}")
    print(f"Difference: {new_total - old_total:.8f} BTC")
    
    # Convert timestamp columns to datetime for comparison
    old_btc_sells = old_btc_sells.copy()
    new_btc_sells = new_btc_sells.copy()
    old_btc_sells['time_stamp'] = pd.to_datetime(old_btc_sells['time_stamp'], errors='coerce')
    new_btc_sells['time_stamp'] = pd.to_datetime(new_btc_sells['time_stamp'], errors='coerce')
    
    # Look for exact duplicates within each file
    old_duplicates = old_btc_sells[old_btc_sells.duplicated(subset=['quantity', 'usd_spot'], keep=False)]
    new_duplicates = new_btc_sells[new_btc_sells.duplicated(subset=['quantity', 'usd_spot'], keep=False)]
    
    print(f"\n===== DUPLICATE ANALYSIS =====")
    print(f"Old file has {len(old_duplicates)} potential duplicate BTC sell transactions")
    print(f"New file has {len(new_duplicates)} potential duplicate BTC sell transactions")
    
    if len(new_duplicates) > 0:
        print("\nDetailed list of potential duplicates in new file:")
        sorted_dupes = new_duplicates.sort_values(by=['quantity', 'usd_spot'])
        
        # Group by quantity and price to find actual duplicates
        for (quantity, price), group in sorted_dupes.groupby(['quantity', 'usd_spot']):
            if len(group) > 1:
                print(f"\n{len(group)} transactions with quantity {quantity:.8f} BTC at price ${price:.2f}:")
                for _, row in group.iterrows():
                    print(f"  - ID {row.name}: {row['time_stamp']} from source: {os.path.basename(row['source'])}")
    
    # Check for same-day transactions that might be duplicates with timezone differences
    print("\n===== TIMEZONE-BASED DUPLICATES =====")
    
    # Find transactions with matching quantity and price but different timestamps
    duplicate_count = 0
    for _, row1 in new_btc_sells.iterrows():
        for _, row2 in new_btc_sells.iterrows():
            if row1.name != row2.name and abs(row1['quantity'] - row2['quantity']) < 0.00001:
                # Same quantity, check price
                if abs(row1['usd_spot'] - row2['usd_spot']) < 0.01:
                    # Same price, check if timestamps are within 24 hours
                    if pd.notna(row1['time_stamp']) and pd.notna(row2['time_stamp']):
                        time_diff_seconds = abs((row1['time_stamp'] - row2['time_stamp']).total_seconds())
                        # Check for timezone difference (7-9 hours difference)
                        if 25000 < time_diff_seconds < 32400:  # 7-9 hours in seconds
                            duplicate_count += 1
                            print(f"\nPossible timezone duplicate:")
                            print(f"  1. ID {row1.name}: {row1['quantity']} BTC at ${row1['usd_spot']} - {row1['time_stamp']}")
                            print(f"     Source: {os.path.basename(row1['source'])}")
                            print(f"  2. ID {row2.name}: {row2['quantity']} BTC at ${row2['usd_spot']} - {row2['time_stamp']}")
                            print(f"     Source: {os.path.basename(row2['source'])}")
                            print(f"  Time difference: {time_diff_seconds/3600:.2f} hours")
    
    if duplicate_count == 0:
        print("No timezone-based duplicates found")
    else:
        print(f"\nFound {duplicate_count} possible timezone-based duplicates")
        
    # Check if any transactions from old file are missing in new file
    print("\n===== MISSING TRANSACTIONS =====")
    missing_count = 0
    for _, old_row in old_btc_sells.iterrows():
        found = False
        for _, new_row in new_btc_sells.iterrows():
            # Check if quantities match within tolerance
            if abs(old_row['quantity'] - new_row['quantity']) < 0.00001:
                # Check if prices match within tolerance
                if abs(old_row['usd_spot'] - new_row['usd_spot']) < 0.01:
                    found = True
                    break
        
        if not found:
            missing_count += 1
            print(f"Transaction from old file may be missing in new file:")
            print(f"  ID {old_row.name}: {old_row['quantity']} BTC at ${old_row['usd_spot']} - {old_row['time_stamp']}")
            print(f"  Source: {os.path.basename(old_row['source'])}")
    
    if missing_count == 0:
        print("No transactions appear to be missing from old file")
    else:
        print(f"Found {missing_count} transactions from old file that may be missing in new file")

    print("\n===== CONCLUSION =====")
    if new_total < old_total:
        print(f"ISSUE CONFIRMED: New file shows LESS total BTC sold ({new_total:.8f}) compared to old file ({old_total:.8f})")
        print(f"Difference: {old_total - new_total:.8f} BTC less in new file")
    else:
        print(f"New file shows MORE total BTC sold ({new_total:.8f}) compared to old file ({old_total:.8f})")
        print(f"Difference: {new_total - old_total:.8f} BTC more in new file")

if __name__ == "__main__":
    analyze_btc_sells()
