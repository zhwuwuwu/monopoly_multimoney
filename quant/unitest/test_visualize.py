import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from framework.visualize import plot_equity, compare_equity

class TestVisualize(unittest.TestCase):

    def setUp(self):
        self.history = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'total_value': [1000, 1100]
        })
        
    @patch('framework.visualize.plt')
    def test_plot_equity(self, mock_plt):
        # Setup mock figure/ax
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        # Test default (show)
        plot_equity(self.history)
        mock_plt.subplots.assert_called_once()
        mock_ax.plot.assert_called()
        mock_plt.show.assert_called_once()
        
        # Reset
        mock_plt.reset_mock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        # Test save
        plot_equity(self.history, save_path='test.png')
        mock_plt.savefig.assert_called_with('test.png', dpi=300, bbox_inches='tight')

    @patch('framework.visualize.plt')
    def test_compare_equity(self, mock_plt):
        # Setup mock
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        experiments = [
            {'history': self.history, 'params': {'strategy': 'S1'}},
            {'history': self.history, 'params': {'strategy': 'S2', 'label': 'Strategy 2'}}
        ]
        
        compare_equity(experiments)
        self.assertEqual(mock_ax.plot.call_count, 2)
        mock_plt.show.assert_called()

    @patch('framework.visualize.plt')
    def test_empty_dataframe(self, mock_plt):
        plot_equity(pd.DataFrame())
        mock_plt.subplots.assert_not_called()

if __name__ == '__main__':
    unittest.main()
