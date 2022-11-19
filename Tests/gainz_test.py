from transactions import Transactions
import pandas as pd
from time import strftime
import os


if __name__ == "__main__":
    transactions = Transactions(view='./App Test Data/Golden_init.xlsx')

    transactions.auto_link(asset=None, algo="fifo")
    filename_fifo_output = transactions.save(description="Created in gainz_test.py")

    df1 = pd.read_excel('./App Test Data/Golden_fifo.xlsx', sheet_name="All Transactions", usecols=["id", "quantity", "name", "trans_type", "time_stamp", "links"], index_col=0)
    df2 = pd.read_excel(filename_fifo_output, sheet_name="All Transactions", usecols=["id", "quantity", "name", "trans_type", "time_stamp", "links"], index_col=0)

    df1.sort_index(inplace=True)
    df2.sort_index(inplace=True)


    if df1.equals(df2) is not True:

        print(f"All Links Fifo Dataframe is NOT equal!\n")

        print(f"Quantity Dataframes Match: {df1['quantity'].equals(df2['quantity'])}")
        print(f"Name Dataframes Match: {df1['name'].equals(df2['name'])}")
        print(f"Transaction Type Dataframes Match: {df1['trans_type'].equals(df2['trans_type'])}")
        print(f"Time Stamp Dataframes Match: {df1['time_stamp'].equals(df2['time_stamp'])}")
        print(f"Links Dataframes Match: {df1['links'].equals(df2['links'])}")

        df_compare = df1.compare(df2, align_axis=1)

        df_compare.to_excel(f"./App Test Data/compare_{strftime('Y%Y-M%m-D%d_H%H-M%M-S%S')}.xlsx") 
 

    else:
        print("All Links Fifo Dataframe is equal!")


    os.remove(filename_fifo_output)

    # import ipdb
    # ipdb.set_trace()

