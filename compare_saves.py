import pandas as pd
import os

# Define the files to analyze
OLD_FILE = "saves/saved_Y2024-M04-D01_H18-M47-S46.xlsx"
NEW_FILE = "saves/saved_Y2025-M04-D12_H09-M36-S15.xlsx"

# Load data
print(f"Loading files: {OLD_FILE} and {NEW_FILE}")
old_df = pd.read_excel(OLD_FILE, sheet_name="All Transactions")
new_df = pd.read_excel(NEW_FILE, sheet_name="All Transactions")

print(f"\nBasic file stats:")
print(f"Old file: {len(old_df)} total transactions")
print(f"New file: {len(new_df)} total transactions")
print(f"Difference: {len(new_df) - len(old_df)} additional transactions in new file")

# Filter for BTC sell transactions
old_btc_all = old_df[old_df['symbol'] == 'BTC']
new_btc_all = new_df[new_df['symbol'] == 'BTC']

old_btc_sells = old_df[(old_df['symbol'] == 'BTC') & (old_df['trans_type'] == 'sell')]
new_btc_sells = new_df[(new_df['symbol'] == 'BTC') & (new_df['trans_type'] == 'sell')]

# Process timestamps 
old_btc_sells['timestamp'] = pd.to_datetime(old_btc_sells['time_stamp'], errors='coerce')
new_btc_sells['timestamp'] = pd.to_datetime(new_btc_sells['time_stamp'], errors='coerce')
old_btc_sells['year'] = old_btc_sells['timestamp'].dt.year
new_btc_sells['year'] = new_btc_sells['timestamp'].dt.year

print(f"\nBTC transaction stats:")
print(f"Old file: {len(old_btc_all)} BTC transactions, {len(old_btc_sells)} sells")
print(f"New file: {len(new_btc_all)} BTC transactions, {len(new_btc_sells)} sells")
print(f"Difference: {len(new_btc_all) - len(old_btc_all)} additional BTC transactions, {len(new_btc_sells) - len(old_btc_sells)} additional sells")

# Calculate BTC sell totals by year
print("\nBTC sell transactions by year:")
old_year_group = old_btc_sells.groupby('year')['quantity'].agg(['sum', 'count'])
new_year_group = new_btc_sells.groupby('year')['quantity'].agg(['sum', 'count'])

print("\nOld file BTC sells by year:")
print(old_year_group)

print("\nNew file BTC sells by year:")
print(new_year_group)

# Compare 2023 specifically
old_2023 = old_btc_sells[old_btc_sells['year'] == 2023]
new_2023 = new_btc_sells[new_btc_sells['year'] == 2023]

print(f"\n2023 BTC SELL COMPARISON:")
print(f"Old file: {len(old_2023)} transactions totaling {old_2023['quantity'].sum():.8f} BTC")
print(f"New file: {len(new_2023)} transactions totaling {new_2023['quantity'].sum():.8f} BTC") 
print(f"Difference: {len(new_2023) - len(old_2023)} additional transactions, {new_2023['quantity'].sum() - old_2023['quantity'].sum():.8f} BTC")

# Look for duplicates in new file
print("\nChecking for potential duplicates in 2023 sells...")
new_2023['date'] = new_2023['timestamp'].dt.date
duplicates = new_2023[new_2023.duplicated(['date', 'quantity'], keep=False)].sort_values(['date', 'quantity'])

if len(duplicates) > 0:
    print(f"Found {len(duplicates)} potential duplicate records in 2023:")
    for i, row in duplicates.iterrows():
        print(f"- {row['date']} | {row['quantity']:.8f} BTC | ${row['usd_spot']:.2f} | Source: {row['source']}")
else:
    print("No duplicates found in 2023 BTC sell transactions.")

# Compare data sources
print("\n2023 BTC sell sources in new file:")
source_counts = new_2023['source'].value_counts()
print(source_counts)

# Examine the newly added transactions
print("\nExamining newly added 2023 BTC sell transactions...")
new_transactions = []

# Create a set of unique identifiers for old transactions
old_trans_set = set()
for _, row in old_2023.iterrows():
    # Create a unique identifier based on date+quantity+price
    old_trans_set.add((
        row['timestamp'].date(),
        round(row['quantity'], 8),
        round(row['usd_spot'], 2)
    ))

# Find transactions in new file that don't match any in old file
for _, row in new_2023.iterrows():
    trans_id = (
        row['timestamp'].date(),
        round(row['quantity'], 8), 
        round(row['usd_spot'], 2)
    )
    if trans_id not in old_trans_set:
        new_transactions.append((
            row['timestamp'], 
            row['quantity'],
            row['usd_spot'],
            row['source']
        ))

if new_transactions:
    print(f"Found {len(new_transactions)} new 2023 transactions not in the old file:")
    for i, (ts, qty, price, source) in enumerate(new_transactions):
        print(f"{i+1}. {ts.strftime('%Y-%m-%d %H:%M:%S')} | {qty:.8f} BTC | ${price:.2f} | {source}")
else:
    print("No new unique transactions found in 2023.")

print("\nAnalysis complete!")
