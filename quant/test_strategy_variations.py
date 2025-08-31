#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse
import os
import sys
import calendar
from typing import Dict, List, Any, Optional, Union, Tuple

# 确保中文显示正常
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体
plt.rcParams['axes.unicode_minus'] = False    # 解决负号显示问题

# 导入自定义模块
from util.market_data_handler import MarketDataHandler
from strategy.b1_strategy import B1Strategy, ConditionType
from b1_stock_filter import B1StockFilter, configure_strategy_variant

class StrategyVariationTester:
    """
    B1策略变体测试类
    用于测试和比较B1策略的不同变体的收益表现
    """
    def __init__(self, 
                 data_handler: Optional[MarketDataHandler] = None,
                 history_days: int = 120,  # 增加历史数据天数以支持更长的持有期
                 verbose: bool = True):
        """
        初始化策略变体测试器
        :param data_handler: 市场数据处理器实例，如果为None则创建新实例
        :param history_days: 获取历史数据的天数，默认120天
        :param verbose: 是否打印详细信息
        """
        self.data_handler = data_handler if data_handler else MarketDataHandler()
        self.stock_filter = B1StockFilter(data_handler=self.data_handler, 
                                         history_days=history_days,
                                         verbose=verbose)
        self.verbose = verbose
        self.stock_data_dict = {}  # 缓存股票数据
        self.results = []  # 保存测试结果
        self.daily_results = {}  # 保存每日测试结果 {date: results}
        self.candidate_stocks = []  # 初步筛选的候选股票
        self.benchmark_returns = {}  # 基准收益
        
    def prepare_variations(self) -> List[Dict[str, Any]]:
        """
        准备不同的策略变体配置
        :return: 策略变体配置列表
        """
        # 创建几种不同的策略变体进行测试
        strategy_variations = [
            {
                "name": "默认B1策略(仅J<0)",
                "variant": "default"
            },
            # {
            #     "name": "完整B1策略",
            #     "variant": "b1+"
            # },
            # {
            #     "name": "B1+放量策略",
            #     "variant": "volume_surge"
            # },
            # {
            #     "name": "宽松条件组合策略",
            #     "variant": "loose"
            # },
            # {
            #     "name": "加权组合策略",
            #     "variant": "weighted"
            # }
        ]
        return strategy_variations
    
    def prepare_stock_pools(self, pool_type: str = "all") -> Dict[str, List[str]]:
        """
        准备股票池
        :param pool_type: 股票池类型，可选值为"hs300"、"zz500"、"all_a"或"all"
        :return: 股票池字典 {pool_name: symbols_list}
        """
        stock_pools = {}
        
        if pool_type == "hs300" or pool_type == "all":
            stock_pools["hs300"] = self.stock_filter.prepare_stock_pool("hs300")
            
        if pool_type == "zz500" or pool_type == "all":
            stock_pools["zz500"] = self.stock_filter.prepare_stock_pool("zz500")
            
        if pool_type == "all_a" or pool_type == "all":
            stock_pools["all_a"] = self.stock_filter.prepare_stock_pool("all_a", stock_count=1000)  # 限制数量以提高性能
        
        if not stock_pools:
            raise ValueError(f"无效的股票池类型: {pool_type}")
        
        if self.verbose:
            print(f"准备了股票池:")
            for pool_name, symbols in stock_pools.items():
                print(f"  {pool_name}: {len(symbols)}只股票")
                
        return stock_pools
    
    def load_data_for_date_range(self, 
                               start_date: str, 
                               end_date: str, 
                               symbols: List[str]) -> Dict[str, pd.DataFrame]:
        """
        加载指定日期范围内的股票数据
        :param start_date: 开始日期，格式为 'YYYYMMDD'
        :param end_date: 结束日期，格式为 'YYYYMMDD'
        :param symbols: 股票代码列表
        :return: 股票数据字典 {symbol: dataframe}
        """
        if self.verbose:
            print(f"加载股票数据 ({start_date} 至 {end_date})")
            print("-" * 60)
        
        # 准备股票数据
        stock_data_dict = {}
        for symbol in symbols:
            df = self.data_handler.get_stock_data(symbol, start_date, end_date)
            if df is not None and len(df) > 0:
                stock_data_dict[symbol] = df
        
        if self.verbose:
            print(f"获取到 {len(stock_data_dict)} 只有效股票数据")
        
        self.stock_data_dict = stock_data_dict
        return stock_data_dict
    
    def filter_candidate_stocks(self, 
                              target_date: str, 
                              stock_pools: Dict[str, List[str]]) -> List[str]:
        """
        使用默认B1策略(仅J<0)筛选初步候选股票
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :param stock_pools: 股票池字典
        :return: 候选股票列表
        """
        if self.verbose:
            print(f"\n使用默认B1策略(仅J<0)筛选 {target_date} 的初步候选股票")
            print("-" * 60)
        
        # 合并所有股票池
        all_symbols = []
        for symbols in stock_pools.values():
            all_symbols.extend(symbols)
        
        # 去重
        all_symbols = list(set(all_symbols))
        
        if self.verbose:
            print(f"合并后共有 {len(all_symbols)} 只不重复股票")
        
        # 加载股票数据
        self.stock_filter.load_stock_data(all_symbols, target_date)
        
        # 使用默认B1策略(仅J<0)筛选
        strategy = B1Strategy()
        configure_strategy_variant(strategy, "default")
        
        # 筛选股票
        filtered_results = self.stock_filter.filter_stocks(strategy, target_date)
        
        # 获取候选股票代码
        candidate_stocks = list(filtered_results.keys())
        
        if self.verbose:
            print(f"初步筛选出 {len(candidate_stocks)} 只候选股票")
        
        self.candidate_stocks = candidate_stocks
        return candidate_stocks
    
    def calculate_returns(self, 
                        symbols: List[str], 
                        start_date: str, 
                        end_date: str) -> Dict[str, float]:
        """
        计算指定股票在[start_date, end_date]区间内的收益率
        :param symbols: 股票代码列表
        :param start_date: 开始日期，格式为 'YYYY-MM-DD'
        :param end_date: 结束日期，格式为 'YYYY-MM-DD'
        :return: 收益率字典 {symbol: return_rate}
        """
        returns = {}
        
        # 将输入日期转换为数据抓取所需的YYYYMMDD
        start_fetch = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y%m%d')
        end_fetch = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y%m%d')
        
        # 加载数据
        stock_data = self.load_data_for_date_range(start_fetch, end_fetch, symbols)
        
        # 计算收益率
        for symbol, df in stock_data.items():
            if df is None or len(df) < 2:
                continue

            # 直接使用区间内首末交易日价格
            buy_price = df['close'].iloc[0]
            sell_price = df['close'].iloc[-1]
            return_rate = (sell_price - buy_price) / buy_price
            
            returns[symbol] = return_rate
            
        return returns
    
    def calculate_benchmark_returns(self, 
                                  start_date: str, 
                                  end_date: str,
                                  benchmark_pool: str = "hs300") -> float:
        """
        计算指定股票池在[start_date, end_date]区间内的平均收益率作为基准
        :param start_date: 开始日期，格式为 'YYYY-MM-DD'
        :param end_date: 结束日期，格式为 'YYYY-MM-DD'
        :param benchmark_pool: 基准股票池类型，可选值为"hs300"、"zz500"、"all_a"
        :return: 平均收益率
        """
        if self.verbose:
            print(f"\nBENCHMARK: 计算{benchmark_pool}股票池在[{start_date} -> {end_date}]区间内的平均收益率作为基准")
            print("-" * 60)
        
        # 获取基准股票池
        benchmark_symbols = self.stock_filter.prepare_stock_pool(benchmark_pool)
        
        # 计算收益率
        returns = self.calculate_returns(benchmark_symbols, start_date, end_date)
        
        if self.verbose:
            print(f"基准股票池包含 {len(benchmark_symbols)} 只股票, 有效收益样本: {len(returns)}")
        # 计算平均收益率
        if returns:
            avg_return = sum(returns.values()) / len(returns)
        else:
            avg_return = 0.0
            
        if self.verbose:
            print(f"{benchmark_pool}股票池在[{start_date} -> {end_date}]区间内的平均收益率: {avg_return:.2%}")
            
        # 缓存基准收益：按日期区间键保存
        self.benchmark_returns[(start_date, end_date)] = avg_return
        
        return avg_return
    
    def test_strategy_variant(self, 
                            variant: Dict[str, Any], 
                            start_date: str, 
                            end_date: str) -> Dict[str, Any]:
        """
        测试单个策略变体的收益表现
        :param variant: 策略变体配置
        :param start_date: 开始日期，格式为 'YYYY-MM-DD'
        :param end_date: 结束日期，格式为 'YYYY-MM-DD'
        :return: 测试结果
        """
        if self.verbose:
            print(f"\nTEST STRATEGY: 测试变体: {variant['name']}")
            print("-" * 60)
        
        # 创建策略实例
        strategy = B1Strategy()
        configure_strategy_variant(strategy, variant['variant'])
        
        # 筛选股票
        filtered_results = self.stock_filter.filter_stocks(strategy, start_date)
        
        # 获取筛选出的股票代码
        selected_stocks = list(filtered_results.keys())
        
        if not selected_stocks:
            if self.verbose:
                print(f"策略 {variant['name']} 未筛选出任何股票")
            return {
                "strategy_name": variant['name'],
                "selected_count": 0,
                "avg_return": 0.0,
                "excess_return": 0.0,
                "returns": {},
                "selected_stocks": []
            }
        
        # 计算收益率
        returns = self.calculate_returns(selected_stocks, start_date, end_date)
        
        # 计算平均收益率
        if returns:
            avg_return = sum(returns.values()) / len(returns)
        else:
            avg_return = 0.0
            
        # 计算超额收益率
        # 若已缓存区间基准，则直接取；否则为0
        benchmark_return = self.benchmark_returns.get((start_date, end_date), 0.0)
        excess_return = avg_return - benchmark_return
        
        if self.verbose:
            print(f"策略 {variant['name']} 筛选出 {len(selected_stocks)} 只股票")
            print(f"平均收益率: {avg_return:.2%}")
            print(f"超额收益率: {excess_return:.2%}")
            
        # 保存结果
        result = {
            "strategy_name": variant['name'],
            "selected_count": len(selected_stocks),
            "avg_return": avg_return,
            "excess_return": excess_return,
            "returns": returns,
            "selected_stocks": selected_stocks
        }
        
        return result
    
    def test_all_variants(self, 
                        start_date: str, 
                        end_date: str,
                        benchmark_pool: str = "hs300") -> List[Dict[str, Any]]:
        """
        测试所有策略变体的收益表现
        :param start_date: 开始日期，格式为 'YYYY-MM-DD'
        :param end_date: 结束日期，格式为 'YYYY-MM-DD'
        :param benchmark_pool: 基准股票池类型，可选值为"hs300"、"zz500"、"all_a"
        :return: 测试结果列表
        """
        if self.verbose:
            print(f"\n开始测试所有策略变体在[{start_date} -> {end_date}]区间内的收益表现")
            print("=" * 60)
        
        # 准备策略变体
        strategy_variations = self.prepare_variations()
        
        # 计算基准收益
        benchmark_return = self.calculate_benchmark_returns(start_date, end_date, benchmark_pool)
        # 为与旧的可视化接口兼容，同时以交易日数作为键保存一份
        try:
            sd = datetime.strptime(start_date, '%Y-%m-%d')
            ed = datetime.strptime(end_date, '%Y-%m-%d')
            holding_days_equiv = self.count_trading_days(sd, ed)
            self.benchmark_returns[holding_days_equiv] = benchmark_return
        except Exception:
            pass
        
        # 测试每个策略变体
        results = []
        for variant in strategy_variations:
            result = self.test_strategy_variant(variant, start_date, end_date)
            results.append(result)
            
        self.results = results
        return results
    
    def compare_results(self) -> None:
        """
        比较不同策略变体的收益表现
        """
        if not self.results:
            raise ValueError("请先调用test_all_variants测试策略变体")
            
        if self.verbose:
            print("\n策略变体收益比较:")
            print(f"{'策略名称':<25} {'筛选股票数':<12} {'平均收益率':<12} {'超额收益率':<12}")
            print("-" * 65)
            
            for result in self.results:
                print(f"{result['strategy_name']:<25} {result['selected_count']:<12} "
                      f"{result['avg_return']:<12.2%} {result['excess_return']:<12.2%}")
    
    def visualize_results(self, 
                        holding_days: int, 
                        save_path: str = None) -> None:
        """
        将结果可视化为图表
        :param holding_days: 持有天数
        :param save_path: 保存图表的路径，如果为None则使用默认路径
        """
        if not self.results:
            raise ValueError("请先调用test_all_variants测试策略变体")
            
        if save_path is None:
            save_path = f'strategy_variations_returns_{holding_days}days.png'
            
        # 策略名称
        strategy_names = [result["strategy_name"] for result in self.results]
        
        # 平均收益率
        avg_returns = [result["avg_return"] * 100 for result in self.results]  # 转换为百分比
        
        # 超额收益率
        excess_returns = [result["excess_return"] * 100 for result in self.results]  # 转换为百分比
        
        # 基准收益率
        benchmark_return = self.benchmark_returns.get(holding_days, 0.0) * 100  # 转换为百分比
        benchmark_returns = [benchmark_return] * len(strategy_names)
        
        x = np.arange(len(strategy_names))
        width = 0.25
        
        fig, ax = plt.subplots(figsize=(14, 8))
        rects1 = ax.bar(x - width, avg_returns, width, label='平均收益率(%)')
        rects2 = ax.bar(x, excess_returns, width, label='超额收益率(%)')
        rects3 = ax.bar(x + width, benchmark_returns, width, label='基准收益率(%)')
        
        # 添加数值标签
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.2f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3点垂直偏移
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        autolabel(rects1)
        autolabel(rects2)
        autolabel(rects3)
        
        ax.set_title(f'不同B1策略变体在{holding_days}天持有期内的收益比较')
        ax.set_xticks(x)
        ax.set_xticklabels(strategy_names)
        ax.legend()
        
        # 添加网格线
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 添加零线
        ax.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if self.verbose:
            print(f"\n结果图表已保存至: {save_path}")
            plt.show()
    
    def generate_date_range(self, start_date: str, end_date: str) -> List[str]:
        """
        生成日期范围内的所有日期
        :param start_date: 开始日期，格式为 'YYYY-MM-DD'
        :param end_date: 结束日期，格式为 'YYYY-MM-DD'
        :return: 日期列表，格式为 'YYYY-MM-DD'
        """
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        date_list = []
        current_date = start_date_obj
        
        while current_date <= end_date_obj:
            # 跳过周末
            if current_date.weekday() < 5:  # 0-4 表示周一至周五
                date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
            
        return date_list
     
    # 定义一个辅助函数：向前推进指定个交易日（跳过周六日）
    @staticmethod
    def add_trading_days(d: datetime, n: int) -> datetime:
        if n <= 0:
            return d
        days_added = 0
        cur = d
        while days_added < n:
            cur += timedelta(days=1)
            if cur.weekday() < 5:  # 0-4 为工作日
                days_added += 1
        return cur

    # 计算[start, end)之间的交易日数量（不含end，跳过周末）
    @staticmethod
    def count_trading_days(start: datetime, end: datetime) -> int:
        if end <= start:
            return 0
        cur = start
        days = 0
        while cur < end:
            if cur.weekday() < 5:
                days += 1
            cur += timedelta(days=1)
        return days
    
    def run_for_single_date(self, 
                          target_date: str, 
                          holding_days: int = 10,
                          stock_pools: Dict[str, List[str]] = None,
                          pool_type: str = "all",
                          benchmark_pool: str = "hs300",
                          save_chart: bool = False) -> List[Dict[str, Any]]:
        """
        为单个日期运行测试流程
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :param holding_days: 持有天数
        :param stock_pools: 股票池字典，如果为None则创建新的
        :param pool_type: 股票池类型，可选值为"hs300"、"zz500"、"all_a"或"all"
        :param benchmark_pool: 基准股票池类型，可选值为"hs300"、"zz500"、"all_a"
        :param save_chart: 是否保存图表
        :return: 测试结果列表
        """
        if self.verbose:
            print(f"\n测试日期: {target_date}")
            print("=" * 60)
        
        # 准备股票池
        if stock_pools is None:
            if self.verbose:
                print("准备股票池...")
            stock_pools = self.prepare_stock_pools(pool_type)
        
        # 筛选初步候选股票
        if self.verbose:
            print("筛选初步候选股票...")
        self.filter_candidate_stocks(target_date, stock_pools)
        
        # 测试所有策略变体
        if self.verbose:
            print(f"测试所有策略变体在{holding_days}天持有期内的收益表现...")
        # 根据持有天数生成结束日期（跳过周末）
        start_dt = datetime.strptime(target_date, '%Y-%m-%d')
        end_dt = self.add_trading_days(start_dt, holding_days)
        end_date_str = end_dt.strftime('%Y-%m-%d')
        results = self.test_all_variants(target_date, end_date_str, benchmark_pool)
        
        # 比较结果
        if self.verbose:
            print("比较结果...")
            self.compare_results()
        
        # 可视化结果
        if save_chart:
            if self.verbose:
                print("可视化结果...")
            self.visualize_results(holding_days, save_path=f'strategy_variations_{target_date}_{holding_days}days.png')
        
        # 保存每日结果
        self.daily_results[target_date] = results
            
        return results
    
    def run(self, 
           start_date: str = None,
           end_date: str = None,
           target_date: str = None, 
           holding_days: int = 10,
           pool_type: str = "all",
           benchmark_pool: str = "hs300",
           save_chart: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        运行完整的测试流程，支持日期范围或单一日期
        :param start_date: 开始日期，格式为 'YYYY-MM-DD'，如果指定则进行日期范围测试
        :param end_date: 结束日期，格式为 'YYYY-MM-DD'，如果指定则进行日期范围测试
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'，如果start_date和end_date未指定则使用此参数
        :param holding_days: 持有天数
        :param pool_type: 股票池类型，可选值为"hs300"、"zz500"、"all_a"或"all"
        :param benchmark_pool: 基准股票池类型，可选值为"hs300"、"zz500"、"all_a"
        :param save_chart: 是否保存图表
        :return: 测试结果字典 {date: results}
        """
        # 清空之前的结果
        self.daily_results = {}
        
        # 确定是日期范围测试还是单一日期测试
        if start_date and end_date:
            print(f"测试日期范围: {start_date} 至 {end_date}")
            date_list = self.generate_date_range(start_date, end_date)
            
            if not date_list:
                raise ValueError("生成的日期列表为空，请检查日期范围")
                
            print(f"共有 {len(date_list)} 个交易日需要测试")
            
            # 准备股票池（所有日期共用一个股票池以提高效率）
            print("准备股票池...")
            stock_pools = self.prepare_stock_pools(pool_type)
            
            # 遍历每个日期进行测试
            for i, date in enumerate(date_list):
                print(f"\n进度: {i+1}/{len(date_list)} - 测试日期 {date}")
                self.run_for_single_date(date, holding_days, stock_pools, pool_type, benchmark_pool, save_chart=False)
            
            # 汇总结果并可视化
            print("\n所有日期测试完成，生成汇总结果...")
            self.summarize_results(holding_days)
            
            # 可视化汇总结果
            if save_chart:
                print("可视化汇总结果...")
                self.visualize_summary(holding_days, start_date, end_date)
                
            return self.daily_results
        else:
            # 单一日期测试
            if not target_date:
                raise ValueError("必须指定target_date或者同时指定start_date和end_date")
                
            results = self.run_for_single_date(target_date, holding_days, None, pool_type, benchmark_pool, save_chart=save_chart)
            return {target_date: results}
    
    def summarize_results(self, holding_days: int) -> Dict[str, Dict[str, float]]:
        """
        汇总所有日期的测试结果
        :param holding_days: 持有天数
        :return: 汇总结果字典 {strategy_name: {avg_return, avg_excess_return, win_rate}}
        """
        if not self.daily_results:
            raise ValueError("没有可用的每日测试结果，请先运行测试")
            
        # 初始化汇总结果
        summary = {}
        
        # 获取所有策略名称
        strategy_names = set()
        for date_results in self.daily_results.values():
            for result in date_results:
                strategy_names.add(result["strategy_name"])
        
        # 初始化每个策略的汇总数据
        for strategy_name in strategy_names:
            summary[strategy_name] = {
                "total_return": 0.0,
                "total_excess_return": 0.0,
                "win_days": 0,
                "total_days": 0,
                "avg_selected_count": 0
            }
        
        # 汇总数据
        for date, date_results in self.daily_results.items():
            for result in date_results:
                strategy_name = result["strategy_name"]
                summary[strategy_name]["total_return"] += result["avg_return"]
                summary[strategy_name]["total_excess_return"] += result["excess_return"]
                summary[strategy_name]["avg_selected_count"] += result["selected_count"]
                summary[strategy_name]["total_days"] += 1
                if result["excess_return"] > 0:
                    summary[strategy_name]["win_days"] += 1
        
        # 计算平均值和胜率
        for strategy_name, data in summary.items():
            if data["total_days"] > 0:
                data["avg_return"] = data["total_return"] / data["total_days"]
                data["avg_excess_return"] = data["total_excess_return"] / data["total_days"]
                data["win_rate"] = data["win_days"] / data["total_days"]
                data["avg_selected_count"] = data["avg_selected_count"] / data["total_days"]
            else:
                data["avg_return"] = 0.0
                data["avg_excess_return"] = 0.0
                data["win_rate"] = 0.0
                data["avg_selected_count"] = 0
        
        # 打印汇总结果
        if self.verbose:
            print("\n策略变体汇总结果:")
            print(f"测试周期: {len(self.daily_results)}个交易日, 持有期: {holding_days}天")
            print(f"{'策略名称':<25} {'平均收益率':<12} {'平均超额收益':<12} {'胜率':<10} {'平均选股数':<10}")
            print("-" * 75)
            
            for strategy_name, data in summary.items():
                print(f"{strategy_name:<25} {data['avg_return']:<12.2%} "
                      f"{data['avg_excess_return']:<12.2%} {data['win_rate']:<10.2%} "
                      f"{data['avg_selected_count']:.1f}")
        
        return summary
    
    def visualize_summary(self, 
                        holding_days: int, 
                        start_date: str, 
                        end_date: str,
                        benchmark_pool: str = "hs300") -> None:
        """
        可视化汇总结果
        :param holding_days: 持有天数
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param benchmark_pool: 基准股票池类型
        """
        if not self.daily_results:
            raise ValueError("没有可用的每日测试结果，请先运行测试")
            
        # 获取汇总结果
        summary = self.summarize_results(holding_days)
        
        # 准备数据
        strategy_names = list(summary.keys())
        avg_returns = [summary[name]["avg_return"] * 100 for name in strategy_names]  # 转换为百分比
        avg_excess_returns = [summary[name]["avg_excess_return"] * 100 for name in strategy_names]  # 转换为百分比
        win_rates = [summary[name]["win_rate"] * 100 for name in strategy_names]  # 转换为百分比
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        # 绘制收益率图表
        x = np.arange(len(strategy_names))
        width = 0.35
        
        rects1 = ax1.bar(x - width/2, avg_returns, width, label='平均收益率(%)')
        rects2 = ax1.bar(x + width/2, avg_excess_returns, width, label='平均超额收益率(%)')
        
        # 添加数值标签
        def autolabel(rects, ax):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.2f}%',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3点垂直偏移
                            textcoords="offset points",
                            ha='center', va='bottom')
        
        autolabel(rects1, ax1)
        autolabel(rects2, ax1)
        
        ax1.set_title(f'不同B1策略变体在{holding_days}天持有期内的平均收益比较\n({start_date} 至 {end_date}, 共{len(self.daily_results)}个交易日)')
        ax1.set_xticks(x)
        ax1.set_xticklabels(strategy_names)
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        # 绘制胜率图表
        rects3 = ax2.bar(x, win_rates, width, label='胜率(%)')
        
        autolabel(rects3, ax2)
        
        ax2.set_title(f'不同B1策略变体在{holding_days}天持有期内的胜率比较')
        ax2.set_xticks(x)
        ax2.set_xticklabels(strategy_names)
        ax2.legend()
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.set_ylim(0, 100)  # 胜率范围为0-100%
        
        plt.tight_layout()
        save_path = f'strategy_variations_summary_{start_date}_to_{end_date}_{holding_days}days.png'
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if self.verbose:
            print(f"\n汇总结果图表已保存至: {save_path}")
            plt.show()
        
        # 创建每日收益率趋势图
        self.visualize_daily_trends(holding_days, start_date, end_date)
    
    def visualize_daily_trends(self, 
                             holding_days: int, 
                             start_date: str, 
                             end_date: str) -> None:
        """
        可视化每日收益率趋势
        :param holding_days: 持有天数
        :param start_date: 开始日期
        :param end_date: 结束日期
        """
        if not self.daily_results:
            raise ValueError("没有可用的每日测试结果，请先运行测试")
            
        # 准备数据
        dates = sorted(self.daily_results.keys())
        strategy_names = set()
        for date_results in self.daily_results.values():
            for result in date_results:
                strategy_names.add(result["strategy_name"])
        
        strategy_names = sorted(list(strategy_names))
        
        # 创建每个策略的每日收益率和超额收益率数据
        returns_data = {name: [] for name in strategy_names}
        excess_returns_data = {name: [] for name in strategy_names}
        
        for date in dates:
            date_results = self.daily_results[date]
            for strategy_name in strategy_names:
                # 查找该策略在当天的结果
                strategy_result = next((r for r in date_results if r["strategy_name"] == strategy_name), None)
                
                if strategy_result:
                    returns_data[strategy_name].append(strategy_result["avg_return"] * 100)  # 转换为百分比
                    excess_returns_data[strategy_name].append(strategy_result["excess_return"] * 100)  # 转换为百分比
                else:
                    returns_data[strategy_name].append(0)
                    excess_returns_data[strategy_name].append(0)
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))
        
        # 绘制每日收益率趋势
        for strategy_name in strategy_names:
            ax1.plot(dates, returns_data[strategy_name], marker='o', label=strategy_name)
        
        ax1.set_title(f'不同B1策略变体在{holding_days}天持有期内的每日收益率趋势')
        ax1.set_xlabel('日期')
        ax1.set_ylabel('收益率(%)')
        ax1.legend()
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        # 设置x轴日期格式
        fig.autofmt_xdate()
        
        # 绘制每日超额收益率趋势
        for strategy_name in strategy_names:
            ax2.plot(dates, excess_returns_data[strategy_name], marker='o', label=strategy_name)
        
        ax2.set_title(f'不同B1策略变体在{holding_days}天持有期内的每日超额收益率趋势')
        ax2.set_xlabel('日期')
        ax2.set_ylabel('超额收益率(%)')
        ax2.legend()
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        
        plt.tight_layout()
        save_path = f'strategy_variations_daily_trends_{start_date}_to_{end_date}_{holding_days}days.png'
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        if self.verbose:
            print(f"\n每日趋势图表已保存至: {save_path}")
            plt.show()


def main():
    # 确保命令行参数支持中文
    if sys.version_info[0] == 3:
        sys.stdout.reconfigure(encoding='utf-8')  # Python 3.7+
    
    parser = argparse.ArgumentParser(description='B1策略变体收益测试工具')
    parser.add_argument('--start_date', type=str, help='开始日期，格式为YYYY-MM-DD')
    parser.add_argument('--end_date', type=str, help='结束日期，格式为YYYY-MM-DD')
    parser.add_argument('--date', type=str, help='单一查询日期，格式为YYYY-MM-DD，当未指定start_date和end_date时使用')
    parser.add_argument('--holding_days', type=int, default=10, help='持有天数')
    parser.add_argument('--pool_type', type=str, default='all', choices=['hs300', 'zz500', 'all_a', 'all'], 
                        help='初始股票池类型: hs300(沪深300), zz500(中证500), all_a(所有A股), all(全部)')
    parser.add_argument('--benchmark', type=str, default='hs300', choices=['hs300', 'zz500', 'all_a'], 
                        help='基准股票池类型: hs300(沪深300), zz500(中证500), all_a(所有A股)')
    parser.add_argument('--no_chart', action='store_true', help='不生成图表')
    parser.add_argument('--quiet', action='store_true', help='静默模式，不打印详细信息')
    args = parser.parse_args()
    
    # 禁用代理设置
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    # 创建策略变体测试器并运行测试
    tester = StrategyVariationTester(verbose=not args.quiet)
    
    # 确定是日期范围测试还是单一日期测试
    if args.start_date and args.end_date:
        tester.run(
            start_date=args.start_date,
            end_date=args.end_date,
            holding_days=args.holding_days,
            pool_type=args.pool_type,
            benchmark_pool=args.benchmark,
            save_chart=not args.no_chart
        )
    elif args.date:
        tester.run(
            target_date=args.date,
            holding_days=args.holding_days,
            pool_type=args.pool_type,
            benchmark_pool=args.benchmark,
            save_chart=not args.no_chart
        )
    else:
        print("错误: 必须指定--date参数或同时指定--start_date和--end_date参数")
        sys.exit(1)


if __name__ == "__main__":
    main()


# 示例用法:
# 单一日期测试:
# python test_strategy_variations.py --date 2025-08-01 --holding_days 10
# python test_strategy_variations.py --date 2025-08-01 --holding_days 5 --pool_type hs300 --benchmark hs300

# 日期范围测试:
# python test_strategy_variations.py --start_date 2025-07-01 --end_date 2025-07-31 --holding_days 10
# python test_strategy_variations.py --start_date 2025-08-01 --end_date 2025-08-15 --pool_type zz500 --benchmark zz500

# 使用不同的初始股票池和基准:
# python test_strategy_variations.py --date 2025-08-01 --pool_type all_a --benchmark all_a
# python test_strategy_variations.py --start_date 2025-07-01 --end_date 2025-07-31 --pool_type all --benchmark zz500
