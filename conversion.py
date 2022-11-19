
import itertools

class Conversion:
    # Used to save information on sends to sells, sends/buys to lost, 


    newid = itertools.count()

    def __init__(
        self, 
        input_trans_type, 
        output_trans_type, 
        input_symbol, 
        input_quantity, 
        input_time_stamp, 
        input_usd_spot, 
        input_usd_total,
        reason,
        source="Gainz App") -> None:

        self.id = next(Conversion.newid)

        self.input_trans_type = input_trans_type
        self.output_trans_type = output_trans_type
        self.symbol = input_symbol
        self.quantity = input_quantity
        self.time_stamp = input_time_stamp
        self.usd_spot =  input_usd_spot
        self.usd_total = input_usd_total
        self.reason = reason
        self.source = source
        
       

        
       


                            



