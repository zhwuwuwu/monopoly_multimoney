import unittest
from unittest.mock import MagicMock
import sys
import os
import pandas as pd

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.composite.composite_strategy import CompositeStrategy
from strategies.selection.base_selection import BaseSelection
from strategies.entry.base_entry import BaseEntry
from strategies.exit.base_exit import BaseExit
from strategies.execution.base_execution import BaseExecution

# Mock Implementations
class MockSelection(BaseSelection):
    def select(self, date, pool, data_handler):
        return pool[:2]  # Select top 2

class MockEntry(BaseEntry):
    def get_signals(self, date, pool, data_handler, current_positions):
        # Buy first one
        if pool:
            return {pool[0]: {'weight': 1.0}}
        return {}

class MockExit(BaseExit):
    def get_exit_signals(self, date, positions, data_handler):
        # Exit if holding > 5 days (mock logic)
        return [s for s, p in positions.items() if p.days_held > 5]

class MockExecution(BaseExecution):
    def calculate_order_price(self, symbol, date, direction, data_handler):
        return 100.0

class TestCompositeStrategy(unittest.TestCase):

    def setUp(self):
        self.selection = MockSelection()
        self.entry = MockEntry()
        self.exit = MockExit()
        self.execution = MockExecution()
        self.strategy = CompositeStrategy(
            self.selection, self.entry, self.exit, self.execution, name="TestStrat"
        )
        self.data_handler = MagicMock()
        
    def test_generate_signals_flow(self):
        # Setup context
        date = '2023-01-10'
        universe = ['A', 'B', 'C', 'D']
        current_positions = {} # dict of Position objects
        
        # Test selection
        # Strategy.select_stocks calls self.selection_strategy.select
        selected = self.strategy.select_stocks(date, universe, self.data_handler)
        self.assertEqual(selected, ['A', 'B'])
        
        # Test entry
        # Strategy.get_entry_signals calls self.entry_strategy.get_signals
        signals = self.strategy.get_entry_signals(date, selected, self.data_handler, current_positions)
        self.assertEqual(list(signals.keys()), ['A'])
        
    def test_exit_flow(self):
        date = '2023-01-20'
        # Mock positions with days held
        pos_A = MagicMock()
        pos_A.days_held = 6
        pos_B = MagicMock()
        pos_B.days_held = 2
        positions = {'A': pos_A, 'B': pos_B}
        
        exits = self.strategy.get_exit_signals(date, positions, self.data_handler)
        self.assertEqual(exits, ['A'])

    def test_execution_price(self):
        price = self.strategy.calculate_execution_price('A', '2023-01-21', 'BUY', self.data_handler)
        self.assertEqual(price, 100.0)

if __name__ == '__main__':
    unittest.main()
