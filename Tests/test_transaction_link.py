import datetime
import unittest

from transaction import Buy, Sell, round_decimals_up
from utils import round_decimals_down


class TransactionLinkTests(unittest.TestCase):
    def test_linked_transactions_defaults_are_not_shared(self):
        buy1 = Buy("BTC", 1, datetime.datetime(2024, 1, 1), 100, "test")
        buy2 = Buy("BTC", 1, datetime.datetime(2024, 1, 2), 100, "test")

        buy1.linked_transactions.append("sentinel")

        self.assertEqual(["sentinel"], buy1.linked_transactions)
        self.assertEqual([], buy2.linked_transactions)

    def test_buy_sell_link_updates_unlinked_quantities_and_gain(self):
        buy = Buy("BTC", 2, datetime.datetime(2024, 1, 1), 100, "test")
        sell = Sell("BTC", 1.25, datetime.datetime(2024, 2, 1), 250, "test")

        link = sell.link_transaction(buy, 1.25)

        self.assertAlmostEqual(0, sell.unlinked_quantity)
        self.assertAlmostEqual(0.75, buy.unlinked_quantity)
        self.assertAlmostEqual(187.5, link.profit_loss)
        self.assertEqual("BTC", link.symbol)

    def test_link_cannot_exceed_unlinked_quantity(self):
        buy = Buy("ETH", 1, datetime.datetime(2024, 1, 1), 1000, "test")
        sell = Sell("ETH", 1, datetime.datetime(2024, 2, 1), 1100, "test")

        with self.assertRaises(ValueError):
            sell.link_transaction(buy, 1.1)

    def test_uid_can_be_restored_from_persistence(self):
        buy = Buy("SOL", 1, datetime.datetime(2024, 1, 1), 50, "test", uid="known-id")

        self.assertEqual("known-id", buy.uid)

    def test_rounding_helpers_use_decimal_strings(self):
        self.assertEqual(0.3, round_decimals_down(0.1 + 0.2, decimals=1))
        self.assertEqual(0.4, round_decimals_up(0.30000000000000004, decimals=1))


if __name__ == "__main__":
    unittest.main()
