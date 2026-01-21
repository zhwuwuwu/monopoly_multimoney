import unittest
from unittest.mock import MagicMock, patch
import argparse
import sys
import os

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from framework.cli import load_yaml_config, merge_config_and_args, build_strategy_from_config, cmd_backtest

class TestCLI(unittest.TestCase):

    def setUp(self):
        # Create a basic namespace for args
        self.default_args = argparse.Namespace(
            start='2023-01-01',
            end='2023-01-31',
            initial=1000000,
            preset=None,
            config=None,
            selection=None,
            entry=None,
            exit=None,
            execution=None,
            name=None,
            max_positions=10,
            universe=300,
            commission=0.0003,
            slippage_bp=10
        )

    def test_merge_config_and_args(self):
        config = {
            'backtest': {
                'start': '2024-01-01',
                'initial': 2000000,
                'universe': 500
            }
        }
        
        # Scenario 1: Config matches, args default provided by parser are usually present but maybe None if not set
        # But here we are passing an args object.
        # Framework logic: user provided args override config.
        # How does it know if user provided it? checks provided_args set from sys.argv.
        
        with patch('sys.argv', ['cli.py', 'backtest']):
            merged = merge_config_and_args(config, self.default_args, 'backtest')
            self.assertEqual(merged.start, '2024-01-01')
            self.assertEqual(merged.initial, 2000000)
            self.assertEqual(merged.universe, 500)

        # Scenario 2: User overrides start via CLI
        with patch('sys.argv', ['cli.py', 'backtest', '--start', '2025-01-01']):
            # We must simulate that 'start' is in args as '2025-01-01' because parser would have put it there
            args = argparse.Namespace(**vars(self.default_args))
            args.start = '2025-01-01'
            
            merged = merge_config_and_args(config, args, 'backtest')
            self.assertEqual(merged.start, '2025-01-01') # Should keep CLI arg
            self.assertEqual(merged.initial, 2000000) # Should take config

    @patch('framework.cli.get_preset_config')
    @patch('framework.cli.build_custom_strategy')
    def test_build_strategy_preset(self, mock_build, mock_get_preset):
        args = argparse.Namespace(preset='test_preset')
        mock_get_preset.return_value = {
            'selection': 's1', 'entry': 'e1', 'exit': 'ex1', 'execution': 'tx1',
            'selection_params': {'p': 1}
        }
        
        build_strategy_from_config({}, args)
        
        mock_get_preset.assert_called_with('test_preset')
        mock_build.assert_called_with(
            selection_name='s1',
            entry_name='e1',
            exit_name='ex1',
            execution_name='tx1',
            selection_params={'p': 1},
            entry_params=None,
            exit_params=None,
            name='test_preset',
            validate=True
        )

    @patch('framework.cli.BacktestEngine')
    @patch('framework.cli.build_strategy_from_config')
    def test_cmd_backtest_flow(self, mock_build_strat, mock_engine_cls):
        # Setup mocks
        mock_strat = MagicMock()
        mock_strat.to_dict.return_value = {'name': 'mock_strat'}
        mock_build_strat.return_value = mock_strat
        
        mock_engine_instance = mock_engine_cls.return_value
        mock_engine_instance.run.return_value = {
            'metrics': {'total_return': 0.1},
            'history': [],
            'trades': [],
            'strategy_config': {}
        }

        # Run command
        with patch('strategies.composite.registry.STRATEGY_BUILDERS', {}) as mock_registry:
            cmd_backtest(self.default_args)
            
            # Check strategy built
            mock_build_strat.assert_called()
            
            # Check engine init and run
            mock_engine_cls.assert_called()
            mock_engine_instance.run.assert_called_with(
                '2023-01-01', '2023-01-31',
                max_positions=10, universe_size=300,
                commission_rate=0.0003, slippage_bp=10
            )
            
            # Check registry injection
            self.assertIn('__temp_cli_strategy__', mock_registry)

if __name__ == '__main__':
    unittest.main()
