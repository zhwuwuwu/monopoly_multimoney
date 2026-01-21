import unittest
import pandas as pd
from datetime import datetime

from framework.backtester import Backtester
from strategies.exit.base import ExitDecision


class MockDataHandler:
    def __init__(self):
        self._symbols = ['AAA']
        # Pre-build 5 business days of constant prices around 100
        self._dates = pd.date_range('2025-01-06', periods=5, freq='B')
        prices = [100, 100, 100, 100, 100]
        self._df = pd.DataFrame({
            'open': prices,
            'close': prices,
            'high': prices,
            'low': prices,
            'volume': [1_000_000]*5,
        }, index=self._dates)

    def get_hs300_components(self):
        return self._symbols

    def get_stock_data(self, symbol, start_date, end_date):  # noqa: D401
        return self._df.copy()


class MockCompositeStrategy:
    """Minimal composite-like strategy object satisfying Backtester interface."""
    def __init__(self):
        self.issued = False

    def generate_entries(self, market_data):
        # Emit a single BUY signal only once (first available day)
        if not self.issued and market_data:
            self.issued = True
            return [{'symbol': 'AAA', 'stop_loss': None, 'target_price': None}]
        return []

    def evaluate_exit(self, position, bar):
        # Exit after holding >= 2 days
        holding_days = (bar['date'] - position['entry_date']).days
        if holding_days >= 2:
            return ExitDecision(True, reason='time_exit', price=None)
        return ExitDecision(False)


class TestBacktesterCore(unittest.TestCase):
    def test_basic_cycle_with_slippage_and_commission(self):
        dh = MockDataHandler()
        strat = MockCompositeStrategy()
        bt = Backtester(
            data_handler=dh,
            strategy=strat,
            initial_capital=100000,
            max_positions=1,
            commission_rate=0.001,  # 0.1%
            slippage_bp=10.0,        # 10 bp = 0.1%
        )
        res = bt.run('2025-01-06', '2025-01-10', universe_size=1)
        trades = res['trades']
        self.assertEqual(len(trades), 2)  # BUY + SELL
        buy, sell = trades[0], trades[1]
        # Check actions
        self.assertEqual(buy['action'], 'BUY')
        self.assertEqual(sell['action'], 'SELL')
        # Slippage: expected executed prices adjusted
        self.assertAlmostEqual(buy['price'], 100 * (1 + 0.001), places=4)
        self.assertAlmostEqual(sell['price'], 100 * (1 - 0.001), places=4)
        # Commission positive
        self.assertGreater(buy['commission'], 0)
        self.assertGreater(sell['commission'], 0)
        # PnL should be negative given symmetric price & slippage + commissions
        self.assertLess(sell['pnl'], 0)
        # Portfolio history captured
        self.assertGreater(len(res['history']), 0)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
