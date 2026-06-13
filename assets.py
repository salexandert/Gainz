
import math

class Asset:

    def __init__(self, symbol, holdings=None) -> None:

        self.symbol = symbol
        if holdings is None:
            self.holdings = None
        elif math.isnan(holdings):
            self.holdings=None
        else:
            self.holdings = holdings

