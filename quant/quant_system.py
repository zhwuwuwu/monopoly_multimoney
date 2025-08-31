import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import os
import argparse

from util.market_data_handler import MarketDataHandler
from strategy.b1_strategy import B1Strategy

class QuantSystem:
    def __init__(self, strategy, capital=1000000, risk_ratio=0.02, mode='simulation'):
        """
        初始化量化交易系统
        :param strategy: 策略对象，必须实现detect_b1_signal等方法
        :param capital: 初始资金
        :param risk_ratio: 单笔交易风险比例
        :param mode: 运行模式，'simulation'为模拟盘，'real'为实盘
        """
        self.capital = capital
        self.risk_ratio = risk_ratio
        self.mode = mode
        
        # 初始化数据处理器和策略
        self.data_handler = MarketDataHandler()
        self.strategy = strategy
        
        # 交易记录
        self.trades = []
        self.portfolio_history = []
    
    def filter_stocks_by_kdj(self, symbols, start_date, end_date):
        """
        使用KDJ指标进行股票粗筛
        :param symbols: 待筛选的股票代码列表
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 通过筛选的股票代码列表
        """
        print("开始KDJ粗筛...")
        stock_data_dict = {}
        
        # 获取所有股票的历史数据
        for symbol in symbols:
            df = self.data_handler.get_stock_data(symbol, start_date, end_date)
            print(f'df{symbol}:', df)
            if df is not None and len(df) > self.strategy.params['min_trade_days']:
                stock_data_dict[symbol] = df
        
        # 调用策略的filter_stocks_by_kdj方法进行筛选
        filtered_symbols = self.strategy.filter_stocks_by_kdj(stock_data_dict)
        
        print(f"KDJ粗筛后剩余股票数量: {len(filtered_symbols)}/{len(symbols)}")
        return filtered_symbols
    
    def get_strategy_params(self):
        """获取策略参数"""
        return self.strategy.params
    
    def update_strategy_params(self, new_params):
        """更新策略参数"""
        return self.strategy.update_params(new_params)
    
    def backtest(self, start_date, end_date):
        """回测系统"""
        print(f"开始回测: {start_date} 至 {end_date}")
        capital = self.capital
        portfolio_value = [capital]
        dates = pd.date_range(start=start_date, end=end_date)
        
        # 获取沪深300成分股
        all_symbols = self.data_handler.get_hs300_components()
        
        # 使用KDJ指标进行粗筛
        symbols = self.filter_stocks_by_kdj(all_symbols, start_date, end_date)
        
        # 持仓记录 {symbol: {entry_date, entry_price, stop_loss, target_price, shares}}
        positions = {}
        
        for current_date in dates:
            # 跳过非交易日
            if current_date.weekday() >= 5:  # 周六日
                continue
                
            date_str = current_date.strftime('%Y%m%d')
            print(f"处理日期: {current_date.strftime('%Y-%m-%d')}")
            
            # 检查持仓止损/止盈
            positions_to_remove = []
            for symbol, pos in positions.items():
                # 获取当日数据
                df = self.data_handler.get_stock_data(symbol, start_date, end_date)
                if df is None or current_date not in df.index:
                    continue
                    
                current_price = df.loc[current_date, 'close']
                
                # 止损检查
                if current_price <= pos['stop_loss']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    capital += current_price * pos['shares']
                    self.record_trade(symbol, 'sell', 'stop_loss', current_date, 
                                     current_price, pos['shares'], profit)
                    positions_to_remove.append(symbol)
                    
                # 止盈检查
                elif current_price >= pos['target_price']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    capital += current_price * pos['shares']
                    self.record_trade(symbol, 'sell', 'take_profit', current_date, 
                                     current_price, pos['shares'], profit)
                    positions_to_remove.append(symbol)
                    
                # 超过最大持有天数
                elif (current_date - pos['entry_date']).days > self.strategy.params['max_hold_days']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    capital += current_price * pos['shares']
                    self.record_trade(symbol, 'sell', 'timeout', current_date, 
                                     current_price, pos['shares'], profit)
                    positions_to_remove.append(symbol)
            
            # 移除已平仓的持仓
            for symbol in positions_to_remove:
                del positions[symbol]
            
            # 如果有持仓空间，寻找新的交易机会
            if len(positions) < 5:  # 最大持仓5只
                for symbol in symbols:
                    if symbol in positions:
                        continue  # 已持仓
                    
                    df = self.data_handler.get_stock_data(symbol, start_date, end_date)
                    if df is None or current_date not in df.index:
                        continue
                    
                    # 检查B1信号
                    signals = self.strategy.detect_b1_signal(df[:df.index.get_loc(current_date)+1])
                    if signals and signals[-1]['date'] == current_date:
                        signal = signals[-1]
                        
                        # 计算头寸规模
                        risk_per_share = signal['price'] - signal['stop_loss']
                        position_size = (capital * self.strategy.params['position_ratio']) / risk_per_share
                        
                        # 确保有足够资金
                        if position_size * signal['price'] > capital * self.strategy.params['position_ratio']:
                            position_size = (capital * self.strategy.params['position_ratio']) // signal['price']
                        
                        if position_size > 0:
                            # 记录交易
                            cost = position_size * signal['price']
                            capital -= cost
                            positions[symbol] = {
                                'entry_date': current_date,
                                'entry_price': signal['price'],
                                'stop_loss': signal['stop_loss'],
                                'target_price': signal['target_price'],
                                'shares': position_size
                            }
                            self.record_trade(symbol, 'buy', 'B1_signal', current_date, 
                                            signal['price'], position_size, -cost)
            
            # 计算当日投资组合价值
            position_value = sum(
                self.data_handler.get_stock_data(sym, start_date, end_date).loc[current_date, 'close'] * pos['shares']
                for sym, pos in positions.items()
            )
            total_value = capital + position_value
            portfolio_value.append(total_value)
            
            # 记录投资组合状态
            self.portfolio_history.append({
                'date': current_date,
                'cash': capital,
                'position_value': position_value,
                'total_value': total_value,
                'positions': len(positions)
            })
        
        # 回测结束，平掉所有持仓
        for symbol, pos in positions.items():
            df = self.data_handler.get_stock_data(symbol, start_date, end_date)
            current_price = df.loc[end_date, 'close']
            profit = (current_price - pos['entry_price']) * pos['shares']
            capital += current_price * pos['shares']
            self.record_trade(symbol, 'sell', 'close_out', end_date, 
                             current_price, pos['shares'], profit)
        
        return portfolio_value
    
    def record_trade(self, symbol, action, reason, date, price, shares, profit):
        """记录交易"""
        trade = {
            'symbol': symbol,
            'action': action,
            'reason': reason,
            'date': date,
            'price': price,
            'shares': shares,
            'profit': profit
        }
        self.trades.append(trade)
        print(f"{date.strftime('%Y-%m-%d')} {action} {symbol} {shares}股 @ {price:.2f}, 原因: {reason}")
    
    def analyze_backtest(self):
        """分析回测结果"""
        if not self.trades or not self.portfolio_history:
            print("没有回测数据可供分析")
            return
        
        # 创建交易记录DataFrame
        trades_df = pd.DataFrame(self.trades)
        
        # 创建投资组合历史DataFrame
        portfolio_df = pd.DataFrame(self.portfolio_history)
        portfolio_df.set_index('date', inplace=True)
        
        # 计算关键指标
        total_profit = trades_df['profit'].sum()
        win_trades = trades_df[trades_df['profit'] > 0]
        loss_trades = trades_df[trades_df['profit'] < 0]
        win_rate = len(win_trades) / len(trades_df) if len(trades_df) > 0 else 0
        avg_win = win_trades['profit'].mean() if not win_trades.empty else 0
        avg_loss = loss_trades['profit'].mean() if not loss_trades.empty else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        # 计算最大回撤
        portfolio_df['peak'] = portfolio_df['total_value'].cummax()
        portfolio_df['drawdown'] = (portfolio_df['total_value'] - portfolio_df['peak']) / portfolio_df['peak']
        max_drawdown = portfolio_df['drawdown'].min()
        
        # 打印结果
        print("\n========== 回测结果分析 ==========")
        print(f"初始资金: {self.capital:,.2f}")
        print(f"最终资金: {portfolio_df['total_value'].iloc[-1]:,.2f}")
        print(f"总利润: {total_profit:,.2f}")
        print(f"总收益率: {portfolio_df['total_value'].iloc[-1]/self.capital - 1:.2%}")
        print(f"交易次数: {len(trades_df)}")
        print(f"胜率: {win_rate:.2%}")
        print(f"平均盈利: {avg_win:,.2f}")
        print(f"平均亏损: {avg_loss:,.2f}")
        print(f"盈亏比: {profit_factor:.2f}")
        print(f"最大回撤: {max_drawdown:.2%}")
        
        # 绘制资金曲线
        plt.figure(figsize=(12, 6))
        plt.plot(portfolio_df.index, portfolio_df['total_value'], label='Portfolio Value')
        plt.plot(portfolio_df.index, portfolio_df['peak'], label='Peak', linestyle='--')
        plt.fill_between(portfolio_df.index, portfolio_df['total_value'], 
                         portfolio_df['peak'], alpha=0.3, color='red')
        plt.title('Portfolio Performance')
        plt.xlabel('Date')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True)
        plt.show()
        
        return portfolio_df, trades_df
    
    def run_simulation(self, start_date=None, end_date=None):
        """
        运行模拟交易
        :param start_date: 开始日期，默认为当前日期前30天
        :param end_date: 结束日期，默认为当前日期
        """
        if self.mode != 'simulation':
            print("错误：当前模式不是模拟盘，请使用mode='simulation'初始化系统")
            return
            
        print("="*50)
        print("量化系统 - 模拟盘运行")
        print("="*50)
        
        # 设置默认日期范围
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
            
        print(f"模拟交易时间范围: {start_date} 至 {end_date}")
        
        # 获取沪深300成分股
        all_symbols = self.data_handler.get_hs300_components()
        print(f"获取到 {len(all_symbols)} 只沪深300成分股")
        
        # 使用KDJ指标进行粗筛
        symbols = self.filter_stocks_by_kdj(all_symbols, start_date, end_date)
        print('筛选后前10只股票: ', symbols[:10] if len(symbols) >= 10 else symbols, '...')  # 显示前10只股票

        # 模拟每日收盘后运行
        dates = pd.date_range(start=start_date, end=end_date)
        positions = {}  # 当前持仓
        
        for current_date in dates:
            # 跳过非交易日
            if current_date.weekday() >= 5:  # 周六日
                continue
                
            date_str = current_date.strftime('%Y%m%d')
            print(f"\n处理日期: {current_date.strftime('%Y-%m-%d')}")
            
            # 1. 检查现有持仓，执行止损/止盈
            positions_to_remove = []
            for symbol, pos in positions.items():
                # 获取当日数据
                df = self.data_handler.get_stock_data(symbol, 
                                        (current_date - timedelta(days=60)).strftime('%Y%m%d'), 
                                        date_str)
                if df is None or current_date not in df.index:
                    print(f"  跳过 {symbol}: 无当日数据")
                    continue
                    
                current_price = df.loc[current_date, 'close']
                
                # 止损检查
                if current_price <= pos['stop_loss']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    print(f"  [止损] {symbol} @ {current_price:.2f}, 盈亏: {profit:.2f}")
                    positions_to_remove.append(symbol)
                    
                # 止盈检查
                elif current_price >= pos['target_price']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    print(f"  [止盈] {symbol} @ {current_price:.2f}, 盈亏: {profit:.2f}")
                    positions_to_remove.append(symbol)
                    
                # 超过最大持有天数
                elif (current_date - pos['entry_date']).days > self.strategy.params['max_hold_days']:
                    profit = (current_price - pos['entry_price']) * pos['shares']
                    print(f"  [超时] {symbol} @ {current_price:.2f}, 盈亏: {profit:.2f}")
                    positions_to_remove.append(symbol)
            
            # 移除已平仓的持仓
            for symbol in positions_to_remove:
                del positions[symbol]
            
            # 2. 寻找新的交易机会
            if len(positions) < 5:  # 最大持仓5只
                print(f"  当前持仓: {len(positions)}/5, 寻找新交易机会...")
                
                for symbol in symbols[:30]:  # 仅检查前30只股票，提高效率
                    print(f"  检查 {symbol}...")
                    if symbol in positions:
                        continue  # 已持仓
                    
                    # 获取历史数据
                    df = self.data_handler.get_stock_data(symbol, 
                                           (current_date - timedelta(days=60)).strftime('%Y%m%d'), 
                                           date_str)
                    if df is None or current_date not in df.index:
                        continue
                    
                    # 检查信号
                    signals = self.strategy.detect_b1_signal(df[:df.index.get_loc(current_date)+1])
                    if signals and signals[-1]['date'] == current_date:
                        signal = signals[-1]
                        
                        # 计算头寸规模
                        risk_per_share = signal['price'] - signal['stop_loss']
                        position_size = (self.capital * self.strategy.params['position_ratio']) / risk_per_share
                        
                        # 确保有足够资金
                        if position_size * signal['price'] > self.capital * self.strategy.params['position_ratio']:
                            position_size = (self.capital * self.strategy.params['position_ratio']) // signal['price']
                        
                        if position_size > 0:
                            # 记录交易
                            positions[symbol] = {
                                'entry_date': current_date,
                                'entry_price': signal['price'],
                                'stop_loss': signal['stop_loss'],
                                'target_price': signal['target_price'],
                                'shares': position_size
                            }
                            print(f"  [买入信号] {symbol} {position_size}股 @ {signal['price']:.2f}")
                            print(f"    止损价: {signal['stop_loss']:.2f}, 目标价: {signal['target_price']:.2f}")
            
            # 3. 输出当前持仓状态
            if positions:
                print("\n  当前持仓:")
                for symbol, pos in positions.items():
                    days_held = (current_date - pos['entry_date']).days
                    print(f"    {symbol}: {pos['shares']}股 @ {pos['entry_price']:.2f}, 持有{days_held}天")
            else:
                print("\n  当前无持仓")
        
        print("\n模拟交易完成!")
        return positions
    
    def connect_real_trading(self, broker_api):
        """
        连接实盘交易接口
        :param broker_api: 包含API密钥和秘钥的字典
        :return: 实盘交易接口对象
        """
        if self.mode != 'real':
            print("警告：当前模式不是实盘，请使用mode='real'初始化系统")
            print("继续连接实盘接口，但不会执行实际交易")
            
        print("="*50)
        print("量化系统 - 实盘交易接口")
        print("="*50)
        print("注意：实盘交易前请确保:")
        print("1. 已完成券商开户并获取API访问权限")
        print("2. 账户中有足够的资金")
        print("3. 了解交易风险并做好风险控制")
        print("="*50)
        
        # 预留的实盘交易接口
        # 实际实现需要根据券商API进行
        class RealTradingInterface:
            def __init__(self, api_key, api_secret):
                self.api_key = api_key
                self.api_secret = api_secret
                self.connected = False
                self.account_info = None
                
            def connect(self):
                """连接券商API"""
                try:
                    # 这里实现实际的连接逻辑
                    self.connected = True
                    print("成功连接实盘交易接口")
                    # 模拟获取账户信息
                    self.account_info = {
                        'cash_available': 1000000,
                        'total_assets': 1000000,
                        'positions': []
                    }
                    return True
                except Exception as e:
                    print(f"连接失败: {str(e)}")
                    return False
            
            def get_account_info(self):
                """获取账户信息"""
                if not self.connected:
                    print("未连接交易接口")
                    return None
                return self.account_info
            
            def place_order(self, symbol, action, price, shares):
                """下单"""
                if not self.connected:
                    print("未连接交易接口")
                    return False
                
                try:
                    # 实际下单逻辑
                    print(f"实盘下单: {action} {shares}股 {symbol} @ {price}")
                    return True
                except Exception as e:
                    print(f"下单失败: {str(e)}")
                    return False
                    
            def cancel_order(self, order_id):
                """撤单"""
                if not self.connected:
                    print("未连接交易接口")
                    return False
                
                try:
                    print(f"撤销订单: {order_id}")
                    return True
                except Exception as e:
                    print(f"撤单失败: {str(e)}")
                    return False
        
        return RealTradingInterface(broker_api['key'], broker_api['secret'])
