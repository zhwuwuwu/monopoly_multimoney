import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import pandas as pd

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from framework.engine import BacktestEngine

class TestEngine(unittest.TestCase):

    @patch('framework.engine.MarketDataHandler')
    @patch('framework.engine.get_strategy')
    @patch('framework.engine.Backtester')
    def test_run_args_separation(self, mock_backtester_cls, mock_get_strat, mock_data_handler):
        # Setup
        mock_bt_instance = mock_backtester_cls.return_value
        mock_bt_instance.run.return_value = {'history': [], 'trades': [], 'strategy_config': {}}
        
        engine = BacktestEngine(strategy_name='test_strat', strategy_kwargs={'a': 1})
        
        # Test Run
        run_params = {
            'max_positions': 5,          # Should go to init
            'commission_rate': 0.001,    # Should go to init
            'slippage_bp': 5,            # Should go to init
             'lookback_days': 30,        # Should go to init
            'universe_size': 50,         # Should go to run (as it's not in the init list in engine.py?)
                                         # Checking engine.py logic below:
                                         # init_params = ['max_positions', 'commission_rate', 'slippage_bp', 'lookback_days']
            'arbitrary_run_param': 'x'   # Should go to run
        }
        
        engine.run('2023-01-01', '2023-01-31', **run_params)
        
        # Check Backtester init call
        # init_kwargs should contain max_positions, commission_rate, slippage_bp, lookback_days
        _, init_kwargs = mock_backtester_cls.call_args
        self.assertEqual(init_kwargs['max_positions'], 5)
        self.assertEqual(init_kwargs['commission_rate'], 0.001)
        self.assertEqual(init_kwargs['slippage_bp'], 5)
        self.assertEqual(init_kwargs['lookback_days'], 30)
        
        # Check Backtester run call
        # run_kwargs should contain the rest
        run_args, run_kwargs = mock_bt_instance.run.call_args
        self.assertEqual(run_args[0], '2023-01-01')
        self.assertEqual(run_args[1], '2023-01-31')
        self.assertEqual(run_kwargs['universe_size'], 50)
        self.assertEqual(run_kwargs['arbitrary_run_param'], 'x')
    
    @patch('framework.engine.MarketDataHandler')
    @patch('framework.engine.get_strategy')
    @patch('framework.engine.Backtester')
    def test_results_structure(self, mock_backtester_cls, mock_get_strat, mock_data_handler):
        mock_bt = mock_backtester_cls.return_value
        
        # Mock valid return data
        mock_bt.run.return_value = {
            'history': [{'date': '2023-01-01', 'total_assets': 100}],
            'trades': [{'date': '2023-01-01', 'symbol': 'S1', 'action': 'BUY'}],
            'strategy_config': {'name': 'test'}
        }
        
        engine = BacktestEngine()
        res = engine.run('2023-01-01', '2023-01-02')
        
        self.assertIsInstance(res['history'], pd.DataFrame)
        self.assertIsInstance(res['trades'], pd.DataFrame)
        self.assertIn('metrics', res)
        self.assertIn('params', res)
        self.assertEqual(res['strategy_config']['name'], 'test')

if __name__ == '__main__':
    unittest.main()
