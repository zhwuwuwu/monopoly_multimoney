import unittest
import pandas as pd
from framework.performance import compute_equity_metrics, compute_trade_metrics


class TestPerformanceModule(unittest.TestCase):
    def test_compute_equity_metrics_basic(self):
        # Synthetic equity curve (4 business days)
        df = pd.DataFrame({
            'date': pd.date_range('2025-01-06', periods=4, freq='B'),
            'total_value': [100000, 101000, 100500, 102000],
            'cash': [100000, 0, 0, 0],
            'positions': [0, 1, 1, 1]
        })
        metrics = compute_equity_metrics(df)
        self.assertIn('total_return', metrics)
        self.assertAlmostEqual(metrics['total_return'], 0.02, places=4)
        self.assertIn('sharpe', metrics)
        self.assertIsInstance(metrics['sharpe'], float)
        self.assertLessEqual(metrics['max_drawdown'], 0)

    def test_compute_trade_metrics(self):
        trades = [
            {'action': 'BUY', 'pnl': 0, 'holding_days': 0},
            {'action': 'SELL', 'pnl': 100, 'holding_days': 2},
            {'action': 'BUY', 'pnl': 0, 'holding_days': 0},
            {'action': 'SELL', 'pnl': -50, 'holding_days': 1},
        ]
        tm = compute_trade_metrics(trades)
        self.assertEqual(tm['trades_total'], 2)
        self.assertAlmostEqual(tm['win_rate'], 0.5, places=4)
        self.assertAlmostEqual(tm['gross_profit'], 100)
        self.assertAlmostEqual(tm['gross_loss'], -50)
        self.assertAlmostEqual(tm['profit_factor'], 2.0)
        self.assertAlmostEqual(tm['net_profit'], 50)


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
