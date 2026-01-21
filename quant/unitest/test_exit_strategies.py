import unittest
import pandas as pd
from datetime import timedelta

from strategies.exit.advanced_exit import TimeBasedExit, TrailingStopExit, AdvancedExit
from strategies.exit.base import ExitDecision


class TestExitStrategies(unittest.TestCase):
    def setUp(self):
        # simple 6-day price series
        self.dates = pd.date_range('2025-01-06', periods=6, freq='B')
        self.df = pd.DataFrame({'close': [100, 102, 105, 104, 103, 95]}, index=self.dates)

        self.base_pos = {
            'entry_price': 100.0,
            'entry_date': self.dates[0],
            'shares': 1000,
            'stop_loss': 90.0,
            'target_price': 130.0,
            'highest_price': 100.0,
        }

    def _bar(self, idx: int):
        return {'date': self.dates[idx], 'close': float(self.df['close'].iloc[idx])}

    def test_time_based_exit(self):
        pos = self.base_pos.copy()
        exit_rule = TimeBasedExit(max_holding_days=3)
        # advance days without hitting other exits
        for i in range(4):
            decision = exit_rule.evaluate(pos, self._bar(i))
        self.assertTrue(decision.exit)
        self.assertEqual(decision.reason, 'time_stop')

    def test_trailing_stop_exit(self):
        pos = self.base_pos.copy()
        trail = TrailingStopExit(trailing_pct=0.05)  # 5%
        # price rises to 105 then drops to 95 ( >5% retrace from 105)
        for i in range(5):
            decision = trail.evaluate(pos, self._bar(i))
        # After processing bar index 4 (price 103) no exit yet
        self.assertFalse(decision.exit)
        # Next big drop
        decision = trail.evaluate(pos, self._bar(5))
        self.assertTrue(decision.exit)
        self.assertEqual(decision.reason, 'trailing_stop')

    def test_advanced_exit_priority(self):
        # Force trailing before target/time
        pos = self.base_pos.copy()
        adv = AdvancedExit(trailing_pct=0.05, max_holding_days=30)
        for i in range(5):
            decision = adv.evaluate(pos, self._bar(i))
        # Big drop triggers trailing
        decision = adv.evaluate(pos, self._bar(5))
        self.assertTrue(decision.exit)
        self.assertEqual(decision.reason, 'trailing_stop')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
