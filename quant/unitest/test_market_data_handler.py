import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys
from util.market_data_handler import MarketDataHandler

class TestMarketDataHandler(unittest.TestCase):
    """
    MarketDataHandler类的测试用例 - 直接测试akshare接口调用
    """
    
    def setUp(self):
        """测试前的准备工作"""
        print('\n' + '='*10 + "设置测试环境..." + '='*10)
        self.handler = MarketDataHandler()
        # 使用真实的日期范围进行测试
        self.start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        self.end_date = datetime.now().strftime('%Y%m%d')
        print(f"测试日期范围: {self.start_date} 至 {self.end_date}")
    
    def test_init(self):
        """测试初始化"""
        print('\n' + '='*10 + "测试初始化..." + '='*10)
        self.assertIsNone(self.handler.hs300_components)
        self.assertEqual(self.handler.historical_data, {})
        print("初始化测试通过")
    
    def test_get_hs300_components(self):
        """测试获取沪深300成分股"""
        print('\n' + '='*10 + "测试获取沪深300成分股..." + '='*10)
        components = self.handler.get_hs300_components()
        
        # 验证结果
        self.assertIsNotNone(components)
        self.assertIsInstance(components, list)
        self.assertGreater(len(components), 0)
        
        # 验证是否包含一些常见的沪深300成分股
        common_stocks = ['600519', '601318', '600036']  # 贵州茅台、中国平安、招商银行
        for stock in common_stocks:
            if stock in components:
                print(f"成分股列表中包含 {stock}")
            else:
                print(f"注意: 成分股列表中不包含 {stock}，可能是成分股发生了变化")
        
        print(f"获取到 {len(components)} 只沪深300成分股")
    
    def test_get_stock_data(self):
        """测试获取股票历史数据"""
        print('\n' + '='*10 + "测试获取股票历史数据..." + '='*10)
        # 测试获取贵州茅台的历史数据
        stock_code = '600519'
        df = self.handler.get_stock_data(stock_code, self.start_date, self.end_date)
        
        # 验证结果
        self.assertIsNotNone(df)
        self.assertIsInstance(df, pd.DataFrame)
        
        # 验证数据结构
        expected_columns = ['open', 'close', 'high', 'low', 'volume', 'amount', 
                           'amplitude', 'pct_change', 'change', 'turnover',
                           'K1', 'D1', 'J1', 'K2', 'D2', 'J2', 'K', 'D', 'J']
        for col in expected_columns:
            self.assertIn(col, df.columns)
        
        # 验证数据不为空
        self.assertGreater(len(df), 0)
        
        # 打印部分数据
        # print(f"\n{stock_code} 历史数据示例 (最近5条):")
        # print(df.tail(5)[['open', 'close', 'high', 'low', 'volume', 'K', 'D', 'J']])
        
        # 测试缓存机制
        print("\n测试缓存机制...")
        cache_key = f"{stock_code}_{self.start_date}_{self.end_date}"
        self.assertIn(cache_key, self.handler.historical_data)
        
        # 再次获取同一只股票的数据，应该直接从缓存返回
        import time
        start_time = time.time()
        df2 = self.handler.get_stock_data(stock_code, self.start_date, self.end_date)
        end_time = time.time()
        
        # 验证是同一个对象
        self.assertIs(df, df2)
        print(f"从缓存获取数据耗时: {(end_time - start_time)*1000:.2f}毫秒")
    
    def test_calculate_kdj(self):
        """测试KDJ指标计算"""
        print('\n' + '='*10 + "测试KDJ指标计算..." + '='*10)
        # 获取一只股票的数据，用于测试KDJ计算
        stock_code = '600000'
        df = self.handler.get_stock_data(stock_code, self.start_date, self.end_date)
        print(df.tail(5))
        # 验证KDJ指标是否已计算
        self.assertIn('K', df.columns)
        self.assertIn('D', df.columns)
        self.assertIn('J', df.columns)
        
        # 验证K、D值是否在0-100范围内
        self.assertTrue((df['K'] >= 0).all() and (df['K'] <= 100).all())
        self.assertTrue((df['D'] >= 0).all() and (df['D'] <= 100).all())
        
        # 验证两种计算方法的结果是否一致
        # pd.testing.assert_series_equal(df['K'], df['K2'])
        # pd.testing.assert_series_equal(df['D'], df['D2'])
        # pd.testing.assert_series_equal(df['J'], df['J2'])
        
        print("\nKDJ指标计算测试通过")
        print("KDJ指标示例 (最近5条):")
        print(df.tail(5)[['K', 'D', 'J']])
    
    def test_multiple_stocks(self):
        """测试获取多只股票的数据"""
        print('\n' + '='*10 + "测试获取多只股票的数据..." + '='*10)
        # 获取沪深300成分股
        components = self.handler.get_hs300_components()
        
        # 选取前5只股票进行测试
        test_stocks = components[:5]
        print(f"\n测试获取多只股票数据: {test_stocks}")
        
        for stock in test_stocks:
            df = self.handler.get_stock_data(stock, self.start_date, self.end_date)
            if df is not None:
                print(f"{stock}: 获取到 {len(df)} 条数据")
            else:
                print(f"{stock}: 获取数据失败")
    
    def test_error_handling(self):
        """测试错误处理"""
        print('\n' + '='*10 + "测试错误处理..." + '='*10)
        # 测试无效的股票代码
        invalid_stock = '999999'
        print(f"\n测试无效的股票代码: {invalid_stock}")
        df = self.handler.get_stock_data(invalid_stock, self.start_date, self.end_date)
        self.assertIsNone(df)
        
        # 测试无效的日期范围
        invalid_date = '20990101'
        print(f"测试无效的日期范围: {invalid_date}")
        df = self.handler.get_stock_data('600519', invalid_date, invalid_date)
        # 这里不一定会返回None，因为akshare可能会返回空DataFrame或最近的数据
        if df is None:
            print("返回了None，符合预期")
        else:
            print(f"返回了DataFrame，包含 {len(df)} 条数据")


if __name__ == '__main__':
    print("开始测试MarketDataHandler类...")
    unittest.main(defaultTest='TestMarketDataHandler.test_calculate_kdj')
