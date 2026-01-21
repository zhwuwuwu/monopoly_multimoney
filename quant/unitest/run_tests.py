# 测试运行脚本，用于执行所有单元测试
import unittest
import os
import sys
from pathlib import Path

# 确保项目根路径在 sys.path
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.append(str(root))

if __name__ == '__main__':
    # 禁用代理：避免网络外部依赖导致失败
    for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        os.environ[k] = ''

    print("=" * 60)
    print("运行量化交易系统单元测试 (自动发现 test_*.py)")
    print("=" * 60)

    loader = unittest.defaultTestLoader
    suite = loader.discover(start_dir=os.path.dirname(__file__), pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    # 退出码：失败时非零（便于 CI 集成）
    sys.exit(0 if result.wasSuccessful() else 1)
