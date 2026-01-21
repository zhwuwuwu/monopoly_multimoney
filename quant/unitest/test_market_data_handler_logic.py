import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os
import time

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from util.market_data_handler import MarketDataHandler

class TestMarketDataHandlerLogic(unittest.TestCase):
    
    def setUp(self):
        self.handler = MarketDataHandler()
        
    @patch('util.market_data_handler.ak')
    @patch('time.sleep')
    def test_rate_limiting(self, mock_sleep, mock_ak):
        # Setup mock return
        df_mock = pd.DataFrame({
            '日期': ['2023-01-01'], '开盘': [10], '收盘': [11], '最高': [12], '最低': [9], '成交量': [100], '成交额': [1000],
            '振幅': [1], '涨跌幅': [1], '涨跌额': [1], '换手率': [1]
        })
        mock_ak.stock_zh_a_hist.return_value = df_mock
        
        # Call multiple times
        self.handler.get_stock_data('000001', '20230101', '20230105')
        self.handler.get_stock_data('000002', '20230101', '20230105')
        
        # Assert sleep was called (rate limiting)
        # Note: The existing implementation might just put sleep before call in get_stock_data
        self.assertTrue(mock_sleep.called)
        self.assertGreaterEqual(mock_sleep.call_count, 2)
        
    @patch.dict(os.environ, {'HTTP_PROXY': 'http://proxy', 'HTTPS_PROXY': 'https://proxy'})
    def test_proxy_removal_during_init(self):
        # Implementation in MarketDataHandler removes proxy on init
        handler = MarketDataHandler()
        self.assertEqual(os.environ.get('HTTP_PROXY'), '')
        self.assertEqual(os.environ.get('HTTPS_PROXY'), '')

    @patch('util.market_data_handler.ak')
    def test_caching(self, mock_ak):
        df_mock = pd.DataFrame({
            '日期': ['2023-01-01'], '开盘': [10], '收盘': [11], '最高': [12], '最低': [9], '成交量': [100], '成交额': [1000],
            '振幅': [1], '涨跌幅': [1], '涨跌额': [1], '换手率': [1]
        })
        mock_ak.stock_zh_a_hist.return_value = df_mock
        
        # First call
        res1 = self.handler.get_stock_data('000001', '20230101', '20230105')
        self.assertEqual(mock_ak.stock_zh_a_hist.call_count, 1)
        
        # Second call (same params)
        res2 = self.handler.get_stock_data('000001', '20230101', '20230105')
        self.assertEqual(mock_ak.stock_zh_a_hist.call_count, 1) # Should not increase
        self.assertIs(res1, res2) # Same object

    @patch('util.market_data_handler.ak')
    def test_invalid_data_handling(self, mock_ak):
        # Mock empty data
        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame()
        
        res = self.handler.get_stock_data('000001', '20230101', '20230105')
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
