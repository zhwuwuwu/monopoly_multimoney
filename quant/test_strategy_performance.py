import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import os

# 导入自定义模块
from util.market_data_handler import MarketDataHandler
from strategy.b1_strategy import B1Strategy

class StrategyPerformanceTester:
    """
    策略绩效测试类，用于评估选股策略的有效性
    """
    def __init__(self, strategy, market_data_handler):
        """
        初始化策略测试器
        :param strategy: 策略对象，需实现相关选股方法
        :param market_data_handler: 市场数据处理对象
        """
        self.strategy = strategy
        self.data_handler = market_data_handler
        
    def calculate_future_returns(self, symbols, date, future_days_list=[5, 10, 20]):
        """
        计算一组股票在指定日期后的未来收益率
        :param symbols: 股票代码列表
        :param date: 选股日期
        :param future_days_list: 未来天数列表
        :return: 包含未来收益的字典 {symbol: {days: return_rate, ...}, ...}
        """
        result = {}
        end_date = (datetime.strptime(date, '%Y%m%d') + timedelta(days=max(future_days_list) + 10)).strftime('%Y%m%d')
        
        print(f"计算 {len(symbols)} 只股票未来 {future_days_list} 天的收益率...")
        
        for symbol in symbols:
            # 获取足够长的历史数据，确保包含未来天数
            df = self.data_handler.get_stock_data(symbol, date, end_date)
            if df is None or len(df) < 2:  # 确保至少有两天数据
                continue
                
            # 当日收盘价作为基准价格
            try:
                base_date = datetime.strptime(date, '%Y%m%d').date()
                # 找到最接近选股日期的交易日
                closest_date = min(df.index, key=lambda x: abs((x.date() - base_date).days))
                
                base_price = df.loc[closest_date, 'close']
                symbol_returns = {}
                
                # 计算不同时间范围的收益率
                for days in future_days_list:
                    future_date = closest_date + pd.Timedelta(days=days)
                    # 寻找最接近未来日期的交易日
                    future_dates = [d for d in df.index if d >= future_date]
                    if not future_dates:
                        continue
                        
                    future_price = df.loc[min(future_dates), 'close']
                    return_rate = (future_price / base_price) - 1
                    symbol_returns[days] = return_rate
                
                if symbol_returns:  # 只有当计算出收益率时才添加到结果中
                    result[symbol] = symbol_returns
            except Exception as e:
                print(f"计算 {symbol} 未来收益率出错: {str(e)}")
        
        return result
    
    def get_benchmark_returns(self, benchmark_symbol, date, future_days_list=[5, 10, 20]):
        """
        获取基准指数的未来收益率
        :param benchmark_symbol: 基准指数代码，如'000300'代表沪深300
        :param date: 选股日期
        :param future_days_list: 未来天数列表
        :return: 包含未来收益的字典 {days: return_rate, ...}
        """
        end_date = (datetime.strptime(date, '%Y%m%d') + timedelta(days=max(future_days_list) + 10)).strftime('%Y%m%d')
        
        # 获取指数数据
        try:
            df = self.data_handler.get_index_data(benchmark_symbol, date, end_date)
            if df is None or len(df) < 2:
                print(f"获取基准指数 {benchmark_symbol} 数据失败")
                return {}
                
            # 基准日期的收盘价
            base_date = datetime.strptime(date, '%Y%m%d').date()
            closest_date = min(df.index, key=lambda x: abs((x.date() - base_date).days))
            base_price = df.loc[closest_date, 'close']
            
            benchmark_returns = {}
            # 计算不同时间范围的收益率
            for days in future_days_list:
                future_date = closest_date + pd.Timedelta(days=days)
                # 寻找最接近未来日期的交易日
                future_dates = [d for d in df.index if d >= future_date]
                if not future_dates:
                    continue
                    
                future_price = df.loc[min(future_dates), 'close']
                return_rate = (future_price / base_price) - 1
                benchmark_returns[days] = return_rate
            
            return benchmark_returns
        except Exception as e:
            print(f"获取基准指数收益率出错: {str(e)}")
            return {}
    
    def test_strategy(self, start_date, end_date, future_days_list=[5, 10, 20], 
                     benchmark_symbol='000300', show_details=False):
        """
        测试策略在给定时间段内的表现
        :param start_date: 测试开始日期
        :param end_date: 测试结束日期
        :param future_days_list: 未来天数列表，计算这些天数后的收益率
        :param benchmark_symbol: 基准指数代码
        :param show_details: 是否显示个股详细数据
        :return: 测试结果
        """
        # 生成测试日期列表，每隔7天取一个日期点
        test_dates = pd.date_range(start=start_date, end=end_date, freq='7D')
        test_dates = [d.strftime('%Y%m%d') for d in test_dates]
        
        all_returns = {}  # 所有日期的收益率 {date: {symbol: {days: return, ...}, ...}, ...}
        all_benchmark_returns = {}  # 所有日期的基准收益率 {date: {days: return, ...}, ...}
        all_signals = {}  # 所有日期的信号 {date: [symbols], ...}
        
        for date in test_dates:
            print(f"\n处理日期: {date}")
            
            # 获取股票池数据
            all_symbols = self.data_handler.get_hs300_components()
            print(f"获取沪深300成分股: {len(all_symbols)} 只")
            
            # 准备股票数据
            stock_data_dict = {}
            for symbol in all_symbols:
                # 获取历史数据进行策略筛选
                # 使用date前60天的数据，确保有足够的历史数据进行KDJ计算
                history_start = (datetime.strptime(date, '%Y%m%d') - timedelta(days=60)).strftime('%Y%m%d')
                df = self.data_handler.get_stock_data(symbol, history_start, date)
                if df is not None and len(df) > self.strategy.params['min_trade_days']:
                    stock_data_dict[symbol] = df
            
            # 应用策略筛选股票
            filtered_symbols = self.strategy.filter_stocks_by_kdj(stock_data_dict)
            
            # 找出所有满足买入信号的股票
            signal_symbols = []
            for symbol, df in stock_data_dict.items():
                if symbol in filtered_symbols:  # 只检查通过KDJ粗筛的股票
                    signals = self.strategy.detect_b1_signal(df)
                    if signals and (datetime.strptime(date, '%Y%m%d').date() - signals[-1]['date'].date()).days <= 3:
                        signal_symbols.append(symbol)
            
            print(f"符合策略的股票数量: {len(signal_symbols)}/{len(filtered_symbols)}")
            all_signals[date] = signal_symbols
            
            if signal_symbols:
                # 计算未来收益率
                returns = self.calculate_future_returns(signal_symbols, date, future_days_list)
                all_returns[date] = returns
                
                # 获取基准指数收益率
                benchmark_returns = self.get_benchmark_returns(benchmark_symbol, date, future_days_list)
                all_benchmark_returns[date] = benchmark_returns
        
        # 分析结果
        self.analyze_results(all_returns, all_benchmark_returns, all_signals, future_days_list, benchmark_symbol, show_details)
    
    def analyze_results(self, all_returns, all_benchmark_returns, all_signals, future_days_list, benchmark_symbol, show_details):
        """
        分析测试结果
        :param all_returns: 所有日期的收益率
        :param all_benchmark_returns: 所有日期的基准收益率
        :param all_signals: 所有日期的信号
        :param future_days_list: 未来天数列表
        :param benchmark_symbol: 基准指数代码
        :param show_details: 是否显示个股详细数据
        """
        print("\n" + "="*50)
        print("策略测试结果分析")
        print("="*50)
        
        # 整合所有日期的收益率
        strategy_returns = {days: [] for days in future_days_list}
        benchmark_returns = {days: [] for days in future_days_list}
        
        for date, returns in all_returns.items():
            for symbol, symbol_returns in returns.items():
                for days, ret in symbol_returns.items():
                    strategy_returns[days].append(ret)
            
            if date in all_benchmark_returns:
                for days, ret in all_benchmark_returns[date].items():
                    benchmark_returns[days].append(ret)
        
        # 计算平均收益率和胜率
        print("\n未来收益率比较:")
        print(f"{'天数':^10}{'策略平均收益':^15}{'基准收益':^15}{'超额收益':^15}{'胜率':^10}")
        print("-"*65)
        
        for days in future_days_list:
            if strategy_returns[days] and benchmark_returns[days]:
                avg_strategy_return = np.mean(strategy_returns[days])
                avg_benchmark_return = np.mean(benchmark_returns[days])
                excess_return = avg_strategy_return - avg_benchmark_return
                
                # 计算胜率 (超过基准的比例)
                outperform_count = sum(1 for ret in strategy_returns[days] if ret > avg_benchmark_return)
                win_rate = outperform_count / len(strategy_returns[days]) if strategy_returns[days] else 0
                
                print(f"{days:^10}{avg_strategy_return:^15.2%}{avg_benchmark_return:^15.2%}{excess_return:^15.2%}{win_rate:^10.2%}")
        
        # 计算平均选股数量
        avg_signal_count = sum(len(signals) for signals in all_signals.values()) / len(all_signals) if all_signals else 0
        print(f"\n平均每个交易日选出股票数量: {avg_signal_count:.2f}")
        
        # 计算不同持有期的策略收益分布
        plt.figure(figsize=(15, 10))
        for i, days in enumerate(future_days_list):
            plt.subplot(len(future_days_list), 1, i+1)
            if strategy_returns[days]:
                plt.hist(strategy_returns[days], bins=20, alpha=0.7, label='策略收益')
                if benchmark_returns[days]:
                    avg_benchmark = np.mean(benchmark_returns[days])
                    plt.axvline(avg_benchmark, color='r', linestyle='--', 
                               label=f'基准平均收益 ({avg_benchmark:.2%})')
                
                plt.title(f'{days}天持有期收益分布')
                plt.xlabel('收益率')
                plt.ylabel('频率')
                plt.legend()
        
        plt.tight_layout()
        plt.savefig('strategy_performance.png')
        plt.show()
        
        # 如果需要，显示个股详细数据
        if show_details:
            print("\n个股详细收益率:")
            for date, returns in all_returns.items():
                print(f"\n日期: {date}")
                for symbol, symbol_returns in returns.items():
                    returns_str = ", ".join([f"{days}天: {ret:.2%}" for days, ret in symbol_returns.items()])
                    print(f"  {symbol}: {returns_str}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='策略绩效测试工具')
    parser.add_argument('--start_date', type=str, default='20250601', help='测试起始日期')
    parser.add_argument('--end_date', type=str, default='20250801', help='测试结束日期')
    parser.add_argument('--future_days', type=str, default='5,10,20', help='未来天数列表，逗号分隔')
    parser.add_argument('--benchmark', type=str, default='000300', help='基准指数代码，默认沪深300')
    parser.add_argument('--details', action='store_true', help='是否显示个股详细数据')
    args = parser.parse_args()
    
    # 处理未来天数列表
    future_days_list = [int(days.strip()) for days in args.future_days.split(',')]
    
    # 初始化策略和市场数据处理器
    strategy = B1Strategy()
    data_handler = MarketDataHandler()
    
    # 初始化策略测试器
    tester = StrategyPerformanceTester(strategy, data_handler)
    
    # 执行测试
    print("="*50)
    print(f"B1策略绩效测试 - {args.start_date} 至 {args.end_date}")
    print("="*50)
    
    tester.test_strategy(
        start_date=args.start_date, 
        end_date=args.end_date,
        future_days_list=future_days_list,
        benchmark_symbol=args.benchmark,
        show_details=args.details
    )


if __name__ == "__main__":
    # 禁用代理设置
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    main()
