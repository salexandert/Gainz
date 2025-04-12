import pandas as pd
import os
from datetime import datetime

def main():
    # Find the saved files
    old_file = r"C:\Development\Gainz\saves\saved_Y2024-M04-D01_H18-M47-S46.xlsx"
    new_file = r"C:\Development\Gainz\saves\saved_Y2025-M04-D12_H09-M36-S15.xlsx"
    
    print(f"Analyzing BTC transactions between:")
    print(f"- Old file: {os.path.basename(old_file)}")
    print(f"- New file: {os.path.basename(new_file)}")
    
    # Load the transaction data from both files
    old_df = pd.read_excel(old_file, sheet_name="All Transactions")
    new_df = pd.read_excel(new_file, sheet_name="All Transactions")
    
    print(f"\nTotal transactions in old file: {len(old_df)}")
    print(f"Total transactions in new file: {len(new_df)}")
    
    # Filter for only BTC transactions
    old_btc = old_df[old_df['symbol'] == 'BTC']
    new_btc = new_df[new_df['symbol'] == 'BTC']
    
    print(f"\nBTC transactions in old file: {len(old_btc)}")
    print(f"BTC transactions in new file: {len(new_btc)}")
    
    # Convert time_stamp to datetime if needed
    if old_btc['time_stamp'].dtype == 'object':
        old_btc['time_stamp'] = pd.to_datetime(old_btc['time_stamp'], errors='coerce')
    if new_btc['time_stamp'].dtype == 'object':
        new_btc['time_stamp'] = pd.to_datetime(new_btc['time_stamp'], errors='coerce')
    
    # Extract year from timestamp
    old_btc['year'] = old_btc['time_stamp'].dt.year
    new_btc['year'] = new_btc['time_stamp'].dt.year
    
    # Focus on 2023 transactions
    old_btc_2023 = old_btc[old_btc['year'] == 2023]
    new_btc_2023 = new_btc[new_btc['year'] == 2023]
    
    print(f"\n2023 BTC transactions in old file: {len(old_btc_2023)}")
    print(f"2023 BTC transactions in new file: {len(new_btc_2023)}")
    
    # Group by transaction type for 2023
    old_2023_by_type = old_btc_2023.groupby('trans_type').agg(
        count=('quantity', 'count'),
        total_quantity=('quantity', 'sum')
    )
    
    new_2023_by_type = new_btc_2023.groupby('trans_type').agg(
        count=('quantity', 'count'),
        total_quantity=('quantity', 'sum')
    )
    
    print("\n2023 BTC transactions by type (OLD FILE):")
    print(old_2023_by_type)
    
    print("\n2023 BTC transactions by type (NEW FILE):")
    print(new_2023_by_type)
    
    # Analyze specific BTC sell transactions from 2023
    old_sells_2023 = old_btc_2023[old_btc_2023['trans_type'] == 'sell']
    new_sells_2023 = new_btc_2023[new_btc_2023['trans_type'] == 'sell']
    
    print(f"\n2023 BTC sell transactions in old file: {len(old_sells_2023)}")
    print(f"2023 BTC sell transactions in new file: {len(new_sells_2023)}")
    print(f"Difference in number of sell transactions: {len(new_sells_2023) - len(old_sells_2023)}")
    
    # If there are differences, identify the new transactions
    if len(new_sells_2023) > len(old_sells_2023):
        print("\nAnalyzing potentially duplicate 2023 BTC sell transactions...")
        
        # Create a set of transaction signatures from old file (using time and quantity)
        old_signatures = set()
        for _, row in old_sells_2023.iterrows():
            # Round quantity to 8 decimal places for consistent comparison
            qty = round(row['quantity'], 8)
            # Create a signature using the timestamp's date part and quantity
            if pd.notna(row['time_stamp']):
                signature = (row['time_stamp'].date(), qty)
                old_signatures.add(signature)
        
        # Find transactions in the new file that aren't in the old file
        new_transactions = []
        for _, row in new_sells_2023.iterrows():
            if pd.notna(row['time_stamp']):
                qty = round(row['quantity'], 8)
                signature = (row['time_stamp'].date(), qty)
                if signature not in old_signatures:
                    new_transactions.append(row)
        
        if new_transactions:
            print(f"\nFound {len(new_transactions)} new 2023 BTC sell transactions that appear to be duplicates:")
            for i, trans in enumerate(new_transactions, 1):
                print(f"\n{i}. New transaction:")
                print(f"   Date: {trans['time_stamp']}")
                print(f"   Quantity: {trans['quantity']}")
                print(f"   Source: {trans['source']}")
                
                # Find potential matches in old file (same quantity but different timestamps)
                potential_matches = old_sells_2023[
                    (abs(old_sells_2023['quantity'] - trans['quantity']) < 0.00000001)
                ]
                
                if not potential_matches.empty:
                    print(f"   Potential matches in old file:")
                    for _, match in potential_matches.iterrows():
                        time_diff = abs((match['time_stamp'] - trans['time_stamp']).total_seconds())
                        hours_diff = time_diff / 3600
                        print(f"   - Date: {match['time_stamp']} (time diff: {hours_diff:.2f} hours)")
                        print(f"     Quantity: {match['quantity']}")
                        print(f"     Source: {match['source']}")
    
    print("\nAnalysis complete.")

if __name__ == "__main__":
    main()
