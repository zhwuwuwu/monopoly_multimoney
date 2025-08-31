## 系统执行流程说明：
1. 数据获取：

使用AKShare获取沪深300指数数据（2018年至今）

包含开盘价、最高价、最低价、收盘价、成交量

2. 策略开发：

双均线策略（5日均线 & 20日均线）

当短期均线上穿长期均线时产生买入信号

当短期均线下穿长期均线时产生卖出信号

3. 回测系统：

计算策略收益和基准收益

计算关键指标：夏普比率、最大回撤

支持参数优化（本例使用默认参数）

4. 实盘接口预留：

TradeGateway类包含券商连接接口

place_order方法模拟下单功能

实际使用时需替换为券商真实API（如华泰PTrade/广发GFQuant）

5. 可视化：

生成两张图表：价格走势+交易信号、收益曲线对比

图表保存为quant_result.png文件

## 实盘交易准备流程：
当您准备好实盘交易时，需完成以下步骤：

1. 开通证券账户：

选择支持量化交易的券商（如华泰、中信、国泰君安）

申请开通量化交易权限（通常需要资金门槛）

2. 替换交易接口：

```python
# 真实交易接口示例（以VN.PY为例）
from vnpy.gateway.ctp import CtpGateway

class RealTradeGateway:
    def __init__(self):
        self.gateway = CtpGateway()
        
    def connect_broker(self):
        settings = {
            "用户名": "您的账号",
            "密码": "您的密码",
            "经纪商代码": "9999",
            "交易服务器": "tcp://180.168.146.187:10101",
            "行情服务器": "tcp://180.168.146.187:10111"
        }
        self.gateway.connect(settings)
        
    def place_order(self, symbol, amount):
        order_req = {
            "symbol": symbol,
            "exchange": Exchange.SSE,  # 上交所
            "direction": Direction.LONG if amount > 0 else Direction.SHORT,
            "type": OrderType.MARKET,
            "volume": abs(amount)
        }
        return self.gateway.send_order(order_req)
```

3. 风险管理：

设置单日最大亏损限额

添加实时监控报警

初期使用<10%资金进行实盘测试

重要提示：在实际连接券商API前，请务必在模拟环境中充分测试策略。本系统已预留交易接口位置，但未实际连接任何券商，不会产生真实交易。

运行此代码后，您将得到完整的策略回测结果和可视化图表，同时保留了未来实盘交易的扩展接口。