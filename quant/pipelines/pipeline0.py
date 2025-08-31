# -*- coding: utf-8 -*-
"""
量化交易全流程系统 (模拟版)
包含：数据获取 → 策略开发 → 回测 → 实盘接口预留
"""

# ========== 环境设置 ==========
import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# ========== 1. 数据获取模块 ==========
class DataFeed:
    def __init__(self, symbol='sh000300', start_date='2020-01-01'):
        self.symbol = symbol
        self.start_date = start_date
        
    def fetch_data(self):
        """从AKShare获取沪深300指数数据"""
        print("正在获取市场数据...")
        df = ak.stock_zh_index_daily(symbol=self.symbol)
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['date'] >= self.start_date]
        df.set_index('date', inplace=True)
        df.rename(columns={
            'close': 'close',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'volume': 'volume'
        }, inplace=True)
        print(f"获取到{len(df)}条数据，时间范围: {df.index[0].date()} 至 {df.index[-1].date()}")
        return df

# ========== 2. 策略开发模块 ==========
class DualMAStrategy:
    def __init__(self, fast_period=5, slow_period=20):
        self.fast_period = fast_period
        self.slow_period = slow_period
        
    def generate_signals(self, data):
        """生成双均线交易信号"""
        data['fast_ma'] = data['close'].rolling(self.fast_period).mean()
        data['slow_ma'] = data['close'].rolling(self.slow_period).mean()
        
        # 生成交易信号 (1: 买入, -1: 卖出, 0: 持有)
        data['signal'] = 0
        data['signal'] = np.where(data['fast_ma'] > data['slow_ma'], 1, 0)
        data['signal'] = data['signal'].diff()  # 仅在信号变化时交易
        
        return data

# ========== 3. 回测引擎模块 ==========
class Backtester:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        
    def run_backtest(self, data):
        """执行回测"""
        print("开始策略回测...")
        data['position'] = data['signal'].cumsum().fillna(0)
        data['market_return'] = data['close'].pct_change()
        
        # 计算策略收益
        data['strategy_return'] = data['position'].shift(1) * data['market_return']
        
        # 计算累计收益
        data['cum_market_return'] = (1 + data['market_return']).cumprod()
        data['cum_strategy_return'] = (1 + data['strategy_return']).cumprod()
        
        # 计算关键指标
        sharpe_ratio = self.calculate_sharpe(data['strategy_return'])
        max_drawdown = self.calculate_max_drawdown(data['cum_strategy_return'])
        
        print(f"回测完成 | 夏普比率: {sharpe_ratio:.2f} | 最大回撤: {max_drawdown:.2%}")
        return data, sharpe_ratio, max_drawdown
    
    def calculate_sharpe(self, returns, risk_free_rate=0.02/252):
        """计算年化夏普比率"""
        excess_returns = returns - risk_free_rate
        sharpe = np.sqrt(252) * excess_returns.mean() / (excess_returns.std() + 1e-8)
        return sharpe
    
    def calculate_max_drawdown(self, cumulative_returns):
        """计算最大回撤"""
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / peak
        return drawdown.min()

# ========== 4. 实盘交易接口模块 (预留但不执行) ==========
class TradeGateway:
    def __init__(self):
        self.connected = False
    
    def connect_broker(self):
        """连接券商交易接口 (预留)"""
        print("="*50)
        print("实盘交易接口说明：")
        print("1. 此接口预留用于实盘交易，实际使用时需替换为券商API")
        print("2. 需开通券商量化交易权限 (如华泰PTrade/广发GFQuant)")
        print("3. 实际交易前需完成: 开户 → 申请量化接口 → 资金转入")
        print("="*50)
        self.connected = True
        return True
    
    def place_order(self, symbol, amount, price=None, order_type='MARKET'):
        """下单函数 (模拟)"""
        if not self.connected:
            print("错误：未连接交易接口，请先调用connect_broker()")
            return False
            
        action = "买入" if amount > 0 else "卖出"
        print(f"[模拟交易] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {action} {abs(amount)}股 {symbol}")
        return True

# ========== 5. 结果可视化模块 ==========
class Visualizer:
    def plot_results(self, data):
        plt.figure(figsize=(14, 10))
        
        # 价格和均线
        plt.subplot(2, 1, 1)
        plt.plot(data['close'], label='收盘价', alpha=0.7)
        plt.plot(data['fast_ma'], label=f'{strategy.fast_period}日均线', linestyle='--')
        plt.plot(data['slow_ma'], label=f'{strategy.slow_period}日均线', linestyle='--')
        
        # 买卖信号
        buy_signals = data[data['signal'] == 1]
        sell_signals = data[data['signal'] == -1]
        plt.scatter(buy_signals.index, buy_signals['close'], marker='^', color='g', s=100, label='买入信号')
        plt.scatter(sell_signals.index, sell_signals['close'], marker='v', color='r', s=100, label='卖出信号')
        
        plt.title('双均线交易策略')
        plt.legend()
        
        # 收益对比
        plt.subplot(2, 1, 2)
        plt.plot(data['cum_market_return'], label='基准收益')
        plt.plot(data['cum_strategy_return'], label='策略收益')
        plt.title('累计收益对比')
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('quant_result.png')
        print("结果图表已保存至 quant_result.png")

# ========== 主程序 ==========
if __name__ == "__main__":
    # 初始化模块
    data_feed = DataFeed(symbol='sh000300', start_date='2020-01-01')
    strategy = DualMAStrategy(fast_period=5, slow_period=20)
    backtester = Backtester(initial_capital=100000)
    visualizer = Visualizer()
    
    # 实盘接口 (预留)
    trade_gateway = TradeGateway()
    
    # 执行完整流程
    try:
        # 1. 获取数据
        data = data_feed.fetch_data()
        
        # 2. 生成交易信号
        data = strategy.generate_signals(data)
        
        # 3. 回测
        backtest_data, sharpe, max_dd = backtester.run_backtest(data)
        
        # 4. 可视化结果
        visualizer.plot_results(backtest_data)
        
        # 5. 实盘接口演示 (不实际执行)
        if trade_gateway.connect_broker():
            # 模拟交易信号
            last_signal = backtest_data['signal'].iloc[-1]
            if last_signal == 1:
                trade_gateway.place_order('sh000300', 1000)  # 模拟买入
            elif last_signal == -1:
                trade_gateway.place_order('sh000300', -1000)  # 模拟卖出
        
        print("\n系统执行完成！实盘交易接口已预留但未实际连接券商。")
        
    except Exception as e:
        print(f"系统错误: {str(e)}")