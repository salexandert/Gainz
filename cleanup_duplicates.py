#!/usr/bin/env python
"""
Script to clean up duplicate transactions in Gainz database.
This will identify and remove duplicate transactions,
then save the cleaned data to a new file.
"""

import pandas as pd
import os
from datetime import datetime
from openpyxl import load_workbook
import sys

def load_excel_data(file_path):
    """Load transaction data from an Excel file."""
    print(f"Loading data from {file_path}...")
    try:
        # Load the "All Transactions" sheet
        all_trans_df = pd.read_excel(file_path, sheet_name="All Transactions")
        
        # Load any other needed sheets
        links_df = pd.read_excel(file_path, sheet_name="Links", header=0)
        
        # Load assets if available
        try:
            assets_df = pd.read_excel(file_path, sheet_name="Assets", header=0)
        except:
            assets_df = pd.DataFrame()
        
        print(f"Loaded {len(all_trans_df)} transactions")
        return all_trans_df, links_df, assets_df
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        sys.exit(1)

def identify_duplicates(df, tolerance=1e-6):
    """Identify duplicate transactions using smarter logic that accounts for timezone differences."""
    print("Identifying duplicate transactions...")
    
    # Make a copy to avoid modifying the original DataFrame
    df = df.copy()
    
    # Convert timestamp to datetime if it's not already
    if df['time_stamp'].dtype == 'object':
        print("Converting timestamps to datetime objects...")
        df['time_stamp'] = pd.to_datetime(df['time_stamp'], errors='coerce')
        print(f"Timestamp conversion complete, found {df['time_stamp'].isna().sum()} invalid timestamps")
    
    # Create a list to store duplicate indices
    duplicates = []
    duplicate_count = 0
    
    # Debug printouts
    print(f"Total transactions to check: {len(df)}")
    print(f"Sample transaction:\n{df.iloc[0]}")
    
    # Compare each row with all other rows
    for i, row1 in df.iterrows():
        # Skip rows with invalid timestamps
        if pd.isna(row1['time_stamp']):
            continue
            
        for j, row2 in df.iloc[i+1:].iterrows():
            # Skip if already marked as duplicate or has invalid timestamp
            if j in duplicates or pd.isna(row2['time_stamp']):
                continue
            
            # Basic criteria for potential duplicates
            if row1['symbol'] == row2['symbol'] and row1['trans_type'] == row2['trans_type']:
                # Check for quantity match with tolerance
                try:
                    quantity_match = abs(float(row1['quantity']) - float(row2['quantity'])) < max(tolerance, tolerance * abs(float(row1['quantity'])))
                    
                    # Check for price match with tolerance
                    price_match = abs(float(row1['usd_spot']) - float(row2['usd_spot'])) < max(tolerance, tolerance * abs(float(row1['usd_spot'])))
                    
                    if quantity_match and price_match:
                        # Check for time difference - within 1 minute or exactly timezone offset
                        time_diff_seconds = abs((row1['time_stamp'] - row2['time_stamp']).total_seconds())
                        time_match = time_diff_seconds < 60 or (time_diff_seconds % 86400) < 60
                        
                        if time_match:
                            print(f"Found duplicate: {row2['symbol']} {row2['quantity']} @ {row2['time_stamp']} (duplicate of {row1['time_stamp']})")
                            duplicates.append(j)
                            duplicate_count += 1
                except (ValueError, TypeError) as e:
                    print(f"Error comparing rows {i} and {j}: {e}")
                    print(f"Row {i}: {row1['symbol']} {row1['quantity']} {row1['usd_spot']}")
                    print(f"Row {j}: {row2['symbol']} {row2['quantity']} {row2['usd_spot']}")
                    continue
    
    print(f"Found {duplicate_count} duplicate transactions")
    return duplicates

def remove_duplicates(transactions_df, duplicates):
    """Remove identified duplicates from the dataframe."""
    if duplicates:
        print(f"Removing {len(duplicates)} duplicate transactions...")
        return transactions_df.drop(duplicates)
    else:
        print("No duplicates to remove.")
        return transactions_df

def save_clean_data(transactions_df, links_df, assets_df, output_path):
    """Save the cleaned data to a new Excel file."""
    print(f"Saving cleaned data to {output_path}...")
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        transactions_df.to_excel(writer, sheet_name='All Transactions', index=True)
        links_df.to_excel(writer, sheet_name='Links', index=True)
        
        if not assets_df.empty:
            assets_df.to_excel(writer, sheet_name='Assets', index=True)
        
        # Add a description sheet
        description_df = pd.DataFrame({
            'Description': [f"Cleaned data - removed duplicates on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
            'Source': ["cleanup_duplicates.py script"]
        })
        description_df.to_excel(writer, sheet_name='Description', index=False)
    
    print(f"Saved cleaned data with {len(transactions_df)} transactions")

def main():
    # Get the most recent save file
    saves_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saves')
    save_files = [f for f in os.listdir(saves_dir) if f.startswith('saved_') and f.endswith('.xlsx')]
    save_files.sort(reverse=True)  # Sort in descending order to get the newest file first
    
    if not save_files:
        print("No save files found.")
        return
    
    latest_save = os.path.join(saves_dir, save_files[0])
    print(f"Using most recent save file: {latest_save}")
    print(f"All save files found: {save_files}")
    
    # Load data
    transactions_df, links_df, assets_df = load_excel_data(latest_save)
    
    # Identify and remove duplicates
    duplicates = identify_duplicates(transactions_df)
    clean_transactions_df = remove_duplicates(transactions_df, duplicates)
    
    if len(duplicates) > 0:
        # Generate output filename
        output_filename = f"saved_Y{datetime.now().strftime('%Y')}-M{datetime.now().strftime('%m')}-D{datetime.now().strftime('%d')}_H{datetime.now().strftime('%H')}-M{datetime.now().strftime('%M')}-S{datetime.now().strftime('%S')}_cleaned.xlsx"
        output_path = os.path.join(saves_dir, output_filename)
        
        # Save cleaned data
        save_clean_data(clean_transactions_df, links_df, assets_df, output_path)
        print(f"Cleaned data saved to {output_path}")
        
        # Statistics
        print("\nTransaction statistics:")
        print(f"  Before cleaning: {len(transactions_df)} transactions")
        print(f"  After cleaning: {len(clean_transactions_df)} transactions")
        print(f"  Duplicates removed: {len(duplicates)}")
        
        # BTC sell statistics
        btc_sells_before = transactions_df[
            (transactions_df['symbol'] == 'BTC') & 
            (transactions_df['trans_type'] == 'sell')
        ]
        btc_sells_after = clean_transactions_df[
            (clean_transactions_df['symbol'] == 'BTC') & 
            (clean_transactions_df['trans_type'] == 'sell')
        ]
        print("\nBTC sell statistics:")
        print(f"  Before cleaning: {len(btc_sells_before)} transactions, {btc_sells_before['quantity'].sum()} BTC")
        print(f"  After cleaning: {len(btc_sells_after)} transactions, {btc_sells_after['quantity'].sum()} BTC")
    else:
        print("No duplicates found, no new file created.")

if __name__ == "__main__":
    main()
