import akshare as ak
import pandas as pd
import numpy as np

# 数据获取及处理
def get_hs300_data():
    """
    获取沪深300指数的历史数据
    """
    print("Fetching HS300 data...")
    hs300_data = ak.index_zh_a_hist(symbol="sh000300", period="daily", start_date="20100101", end_date="20231001")
    hs300_data.rename(columns={"日期": "date", "收盘": "close", "开盘": "open", "最高": "high", "最低": "low", "成交量": "volume"}, inplace=True)
    hs300_data['date'] = pd.to_datetime(hs300_data['date'])
    hs300_data.set_index('date', inplace=True)
    return hs300_data

# 简单量化策略
def simple_moving_average_strategy(data, short_window=20, long_window=50):
    """
    简单的均线策略
    """
    print("Applying strategy...")
    data['short_ma'] = data['close'].rolling(window=short_window).mean()
    data['long_ma'] = data['close'].rolling(window=long_window).mean()
    data['signal'] = 0
    data.loc[data['short_ma'] > data['long_ma'], 'signal'] = 1
    data.loc[data['short_ma'] <= data['long_ma'], 'signal'] = -1
    return data

# 策略回测
def backtest_strategy(data, initial_capital=100000):
    """
    简单的回测逻辑
    """
    print("Backtesting strategy...")
    data['daily_return'] = data['close'].pct_change()
    data['strategy_return'] = data['signal'].shift(1) * data['daily_return']
    data['cumulative_strategy_return'] = (1 + data['strategy_return']).cumprod()
    data['cumulative_market_return'] = (1 + data['daily_return']).cumprod()
    return data

# 实盘交易接口（预留）
def live_trading_interface(signal):
    """
    实盘交易接口（预留）
    """
    print(f"Received trading signal: {signal}")
    # 此处预留实盘交易逻辑
    # 例如：调用券商API下单
    pass

# 主流程
if __name__ == "__main__":
    # 获取数据
    hs300_data = get_hs300_data()

    # 应用策略
    hs300_data = simple_moving_average_strategy(hs300_data)

    # 回测策略
    backtest_results = backtest_strategy(hs300_data)

    # 输出回测结果
    print("Backtest completed. Final cumulative strategy return:")
    print(backtest_results['cumulative_strategy_return'].iloc[-1])

    # 预留实盘交易接口
    latest_signal = hs300_data['signal'].iloc[-1]
    live_trading_interface(latest_signal)