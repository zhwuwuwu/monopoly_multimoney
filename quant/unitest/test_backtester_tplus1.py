import unittest
import pandas as pd

from framework.backtester import Backtester
from strategies.exit.base import ExitDecision


class MockDataHandler:
    def __init__(self):
        self._symbols = ['AAA']
        # 6 business days to allow entry signal day + next open execution + exit
        self._dates = pd.date_range('2025-02-03', periods=6, freq='B')
        # Create a slight upward drift so trailing/price doesn't matter, we just test next open
        self._df = pd.DataFrame({
            'open': [10, 11, 11, 11, 11, 11],
            'close': [11, 11, 11, 11, 11, 11],
            'high': [11, 11, 11, 11, 11, 11],
            'low': [10, 10, 10, 10, 10, 10],
            'volume': [1000]*6,
        }, index=self._dates)

    def get_hs300_components(self):
        return self._symbols

    def get_stock_data(self, symbol, start_date, end_date):  # noqa: D401
        return self._df.copy()


class MockCompositeStrategy:
    def __init__(self):
        self.issued = False

    def generate_entries(self, market_data):
        # Emit one signal first day only
        if not self.issued and market_data:
            self.issued = True
            return [{'symbol': 'AAA'}]
        return []

    def evaluate_exit(self, position, bar):
        # Exit after holding >= 1 day (so entry at day1 open, exit on day2 close)
        holding_days = (bar['date'] - position['entry_date']).days
        if holding_days >= 1:
            return ExitDecision(True, reason='time_exit', price=None)
        return ExitDecision(False)


class TestBacktesterTPlus1(unittest.TestCase):
    def test_next_open_execution(self):
        dh = MockDataHandler()
        strat = MockCompositeStrategy()
        bt = Backtester(
            data_handler=dh,
            strategy=strat,
            initial_capital=10000,
            max_positions=1,
            execution_mode='next_open',
            slippage_bp=0.0,
            commission_rate=0.0,
        )
        res = bt.run('2025-02-03', '2025-02-10', universe_size=1)
        trades = res['trades']
        # Expect two trades (BUY at next day open=11, SELL later at 11)
        self.assertEqual(len(trades), 2)
        buy, sell = trades[0], trades[1]
        self.assertEqual(buy['action'], 'BUY')
        self.assertEqual(sell['action'], 'SELL')
        # Check that buy date is the second calendar business day, not the first signal day
        self.assertEqual(str(buy['date'].date()), str(dh._dates[1].date()))
        # price executed using open price (11)
        self.assertEqual(buy['price'], 11)
        # signal_date recorded
        self.assertIn('signal_date', buy)
        self.assertEqual(str(buy['signal_date'].date()), str(dh._dates[0].date()))


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
