import unittest
import sys
import os
from datetime import datetime, timedelta

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from util.market_data_handler import MarketDataHandler

class TestConnection(unittest.TestCase):
    
    def setUp(self):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 初始化连接测试...")
        self.handler = MarketDataHandler()
        self.start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        self.end_date = datetime.now().strftime('%Y%m%d')

    def test_connection_workflow(self):
        """测试完整连接流程：获取HS300 -> 获取首支股票行情"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 步骤1: 获取沪深300成分股列表...")
        try:
            components = self.handler.get_hs300_components()
        except Exception as e:
            self.fail(f"获取成分股列表失败: {e}")
            
        self.assertIsNotNone(components)
        self.assertGreater(len(components), 0)
        print(f"   >>> 成功获取 {len(components)} 只成分股")
        
        # 2. 获取第一只股票的数据
        first_stock = components[0]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 步骤2: 获取第一只股票 ({first_stock}) 的详细行情...")
        try:
            df = self.handler.get_stock_data(first_stock, self.start_date, self.end_date)
        except Exception as e:
            self.fail(f"获取股票数据失败: {e}")
            
        self.assertIsNotNone(df)
        self.assertFalse(df.empty)
        print(f"   >>> 获取数据成功！共 {len(df)} 行数据")
        print(f"   >>> 最新日期: {df['日期'].iloc[-1] if '日期' in df.columns else 'N/A'}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 连接测试全部通过！外部数据源工作正常。")

if __name__ == '__main__':
    # 禁用代理，确保直接访问（根据之前环境信息）
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ[k] = ''
        
    unittest.main()
