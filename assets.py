
import math

class Asset:

    def __init__(self, symbol, hodl=None) -> None:

        self.symbol = symbol
        if hodl is None:
            self.hodl = None
        elif math.isnan(hodl):
            self.hodl=None
        else:
            self.hodl = hodl
        
