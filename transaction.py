from link import Link
import itertools
import math

def round_decimals_up(number:float, decimals:int=9):
    """
    Returns a value rounded up to a specific number of decimal places.
    """
    if not isinstance(decimals, int):
        raise TypeError("decimal places must be an integer")
    elif decimals < 0:
        raise ValueError("decimal places has to be 0 or more")
    elif decimals == 0:
        return math.ceil(number)

    factor = 10 ** decimals
    return math.ceil(number * factor) / factor

class Transaction:
    newid = itertools.count()
    
    def __init__(self, symbol: str, quantity: float, usd_spot: float, trans_type: str, time_stamp: str, source: str, linked_transactions=[]) -> None:
        self.id = next(Transaction.newid)
        self.quantity = quantity
        self.name = f"{time_stamp} {self.quantity}"
        self.trans_type = trans_type
        self.time_stamp = time_stamp
        self.links = []
        self.linked_transactions = linked_transactions
        self.multi_link = False
        self.symbol = symbol
        self.usd_spot = usd_spot
        self.source = source
        self._fee = None

    @property
    def fee(self):
        return self._fee
    
    @fee.setter
    def fee(self, value):
        if not isinstance(value, float):
            if value == '':
                value = 0.0
            elif type(value) is str:
                value = float(value)
            else:
                raise ValueError(f"fee value: {value}, Type: {type(value)} ] must be a float")
        
        self._fee = float(value)

        
    def __repr__(self):
        return repr(f"{self.time_stamp} {self.quantity}")

    def __eq__(self, other):
        return self.quantity == other.quantity and self.time_stamp == other.time_stamp and self.trans_type == other.trans_type

    def __hash__(self) -> int:
        return hash((self.quantity, self.symbol, self.usd_spot, self.trans_type))
     
    def calc_multi_link(self):
        if len(self.links) > 1:
            return True
        else:
            return False

    def set_multi_link(self):
        self.multi_link = self.calc_multi_link()

    def link_transaction(self, other, link_quantity):

        receive = None
        sell = None
        buy = None
       
        if self.symbol == other.symbol:

            if self.trans_type.lower() == 'sell' and other.trans_type.lower() == 'buy':

                buy = other
                sell = self
                
            elif self.trans_type.lower() == 'buy' and other.trans_type.lower() == 'sell':

                buy = self
                sell = other

            elif self.trans_type.lower() == 'receive' and other.trans_type.lower() == 'buy':

                receive = self
                buy = other

            elif self.trans_type.lower() == 'buy' and other.trans_type.lower() == 'receive':

                receive = other
                buy = self   
            
            if receive is not None:
                link = Link(transactions=[receive, buy], quantity=link_quantity)
            
            elif buy is not None and sell is not None:
                # print(self.trans_type, other.trans_type)
                link = Link(transactions=[sell, buy], quantity=link_quantity)


            if sell is not None and link not in sell.links:
                sell.links.append(link)

            if receive is not None and link not in receive.links:
                receive.links.append(link)

            if link not in buy.links:
                buy.links.append(link)

            else:
                print(f"Link_quantity is still None!")

            
        else:
            print(f"{self.symbol} <-CANNOT LINK-> {other.symbol}")

        # Update Linked Transactions
        if buy is not None:
            buy.update_linked_transactions()

        if sell is not None:
            sell.update_linked_transactions()

        return link

    @property
    def usd_total(self):
        return self.usd_spot * float(self.quantity)

    @property
    def unlinked_quantity(self):
        # self.update_linked_transactions()

        unlinked_quantity = self.quantity        
        
        for link in self.links:

            if (self.trans_type == 'buy') and (link.trans1.trans_type == 'receive' or link.trans2.trans_type == 'receive'):
                continue
            
            unlinked_quantity -= link.quantity
                       
        return round_decimals_up(unlinked_quantity)

    def update_linked_transactions(self):

        linked_transactions = []
        trans = self
        for link in self.links:
            linked_transactions.append(link.other_transaction(trans=trans))
        
        self.linked_transactions = linked_transactions


class Buy(Transaction):
    def __init__(self, symbol, quantity, time_stamp, usd_spot, source, trans_type='buy', linked_transactions=[]):
        super().__init__(symbol=symbol, quantity=quantity, usd_spot=usd_spot, source=source, time_stamp=time_stamp, trans_type=trans_type, linked_transactions=linked_transactions)

        self.symbol = symbol.upper()
        self.usd_spot = float(usd_spot)
        
        



class Sell(Transaction):
    def __init__(self, symbol, quantity, time_stamp, usd_spot, source, trans_type='sell', linked_transactions=[]):
        super().__init__(symbol=symbol, usd_spot=usd_spot, source=source, quantity=quantity, time_stamp=time_stamp, trans_type=trans_type, linked_transactions=linked_transactions)

        self.symbol = symbol.upper()
        self.usd_spot = float(usd_spot)
        
        


class Send(Transaction):
    def __init__(self, symbol, quantity, time_stamp, source, usd_spot, trans_type='send', linked_transactions=[]):
        super().__init__(symbol=symbol, usd_spot=usd_spot, quantity=quantity, time_stamp=time_stamp, source=source, trans_type=trans_type,  linked_transactions=linked_transactions)

        self.symbol = symbol.upper()
        self.usd_spot = float(usd_spot)
        


class Receive(Transaction):
    def __init__(self, symbol, quantity, time_stamp, source, usd_spot, trans_type='receive', linked_transactions=[]):
        super().__init__(symbol=symbol, usd_spot=usd_spot, quantity=quantity, time_stamp=time_stamp, source=source, trans_type=trans_type,  linked_transactions=linked_transactions)

        self.symbol = symbol.upper()
        self.usd_spot = float(usd_spot)
        
        
