# 测试运行脚本，用于执行所有单元测试
import unittest
import os
import sys

# 添加父目录到搜索路径，以便可以导入主项目中的模块
sys.path.append(os.path.abspath('..'))

# 导入所有测试用例
from test_market_data_handler import TestMarketDataHandler

if __name__ == '__main__':
    # 禁用代理设置
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    print("=" * 60)
    print("运行量化交易系统单元测试")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTest(unittest.makeSuite(TestMarketDataHandler))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
