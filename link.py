import itertools
import math

class Link:

    newid = itertools.count()

    def __init__(self, transactions, quantity) -> None:

        self.id = next(Link.newid)
        self.transactions = sorted(transactions, key=lambda transaction: transaction.trans_type)
        self.quantity = quantity
        self.trans1 = self.transactions[0]
        self.trans2 = self.transactions[1]
        self.proceeds_override = None
        self.cost_basis_override = None
        self.resolution_item_id = ""

        tolerance = 1e-9  # Tolerance for floating-point comparison

        if (self.trans1.unlinked_quantity + tolerance < quantity or
                self.trans2.unlinked_quantity + tolerance < quantity):
            raise ValueError(f"Quantity of link [{quantity}] is greater than\
                \ntrans 1 Type [{self.trans1.trans_type}] [{self.trans1.symbol}] unlinked [{self.trans1.unlinked_quantity}]\
                \nor trans 2 Type [{self.trans2.trans_type}] [{self.trans2.symbol}] unlinked quantity [{self.trans2.unlinked_quantity}]")

        if self.transactions[0].trans_type == 'buy' and self.transactions[1].trans_type == 'sell':
            self.buy = self.trans1
            self.sell = self.trans2

        elif self.transactions[0].trans_type == 'sell' and self.transactions[1].trans_type == 'buy':
            self.buy = self.trans2
            self.sell = self.trans1

        elif self.transactions[0].trans_type == 'receive' and self.transactions[1].trans_type == 'buy':
            self.buy = self.trans2
            self.receive = self.trans1

        elif self.transactions[0].trans_type == 'buy' and self.transactions[1].trans_type == 'receive':
            self.receive = self.trans2
            self.buy = self.trans1

        self.symbol = self.buy.symbol
        self.link_buy_price = self.cost_basis
        self.link_sell_price = self.proceeds
        self.link_sell_date = self.sell.time_stamp
        self.link_buy_date = self.buy.time_stamp
        self.profit_loss = (self.link_sell_price - self.link_buy_price)


    def __hash__(self) -> int:
        return hash(tuple(self.transactions))

    def __str__(self) -> str:
        return f"Name: [{self.transactions[0].name}] Trans Type [{self.transactions[0].trans_type}] Quantity [{self.transactions[0].quantity:.2f}]\
        <-{self.quantity:.2f}-> \
        Name: [{self.transactions[1].name}] Trans Type [{self.transactions[1].trans_type}] Quantity [{self.transactions[1].quantity:.2f}]"

    def __repr__(self):
        return f"Link ID: {self.id} Link Quantity: {self.quantity} Link Type: {self.symbol}"


    @property
    def holding_duration(self):
        sell_time = self.sell.time_stamp
        buy_time = self.buy.time_stamp
        if getattr(sell_time, "tzinfo", None) or getattr(buy_time, "tzinfo", None):
            sell_time = sell_time.replace(tzinfo=None)
            buy_time = buy_time.replace(tzinfo=None)
        holding_time = sell_time - buy_time

        return holding_time



    @property
    def proceeds(self):
        if self.proceeds_override is not None:
            return float(self.proceeds_override)
        return self.sell.prorated_tax_usd(self.quantity)

    @property
    def cost_basis(self):
        if self.cost_basis_override is not None:
            return float(self.cost_basis_override)
        return self.buy.prorated_tax_usd(self.quantity)

    def refresh_prices(self):
        self.link_buy_price = self.cost_basis
        self.link_sell_price = self.proceeds
        self.profit_loss = self.link_sell_price - self.link_buy_price

    def other_transaction(self, trans):
        if trans == self.trans1:
            return self.trans2.name
        else:
            return self.trans1.name


if __name__ == '__main__':
    test_link = Link()
