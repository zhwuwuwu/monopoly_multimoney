#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import os
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

from ..util.market_data_handler import MarketDataHandler
from ..strategy.b1_strategy import B1Strategy, ConditionType

class B1StockFilter:
    """
    B1股票筛选器类
    用于获取特定日期通过B1策略筛选的股票列表
    """
    def __init__(self, 
                 data_handler: Optional[MarketDataHandler] = None,
                 history_days: int = 45,
                 verbose: bool = True):
        """
        初始化B1股票筛选器
        :param data_handler: 市场数据处理器实例，如果为None则创建新实例
        :param history_days: 获取历史数据的天数，默认45天
        :param verbose: 是否打印详细信息
        """
        self.data_handler = data_handler if data_handler else MarketDataHandler()
        self.history_days = history_days
        self.verbose = verbose
        self.stock_data_dict = {}  # 缓存股票数据
        
    def prepare_stock_pool(self, 
                          stock_pool: str = "hs300", 
                          symbols: Optional[List[str]] = None, 
                          stock_count: int = -1) -> List[str]:
        """
        准备股票池
        :param stock_pool: 股票池类型
            - "hs300": 沪深300成分股
            - "zz500": 中证500成分股
            - "all_a": 所有A股上市股票
            - "main": 沪深主板股票（仅600/601/603/605开头的沪市和000开头的深市股票）
            - "custom": 自定义股票池
        :param symbols: 自定义股票池列表，当stock_pool为"custom"时使用
        :param stock_count: 获取的股票数量上限，-1表示使用全部股票不截取
        :return: 股票代码列表
        """
        # 获取股票池
        if stock_pool == "hs300":
            if self.verbose:
                print("使用沪深300股票池")
            all_symbols = self.data_handler.get_hs300_components()
        elif stock_pool == "zz500":
            if self.verbose:
                print("使用中证500股票池")
            all_symbols = self.data_handler.get_zz500_components()
        elif stock_pool == "all_a":
            if self.verbose:
                print("使用所有A股上市股票池")
            all_symbols = self.data_handler.get_all_a_stocks()
        elif stock_pool == "main":
            if self.verbose:
                print("使用沪深主板股票池（沪市主板600/601/603/605、深市主板000开头）")
            all_symbols = self.data_handler.get_main_board_stocks()
        elif stock_pool == "custom" and symbols is not None:
            if self.verbose:
                print("使用自定义股票池")
            all_symbols = symbols
        else:
            if self.verbose:
                print("未指定有效股票池，默认使用沪深300")
            all_symbols = self.data_handler.get_hs300_components()
            
        if stock_count > 0 and stock_count < len(all_symbols):
            # 为避免总是选择同样的股票，可以随机抽样
            import random
            random.seed(42)  # 设置随机种子保证结果可重现
            test_symbols = random.sample(all_symbols, stock_count)
        else:
            # stock_count为-1或大于等于列表长度时，使用全部股票
            test_symbols = all_symbols
        
        if self.verbose:    
            print(f"准备从 {len(test_symbols)} 只股票中筛选...")
            
        return test_symbols
    
    def load_stock_data(self, symbols: List[str], target_date: str) -> Dict[str, pd.DataFrame]:
        """
        加载股票数据
        :param symbols: 股票代码列表
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :return: 股票数据字典 {symbol: dataframe}
        """
        # 计算开始日期（往前推指定天数以获取足够的历史数据）
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        start_date_obj = target_date_obj - timedelta(days=self.history_days)
        start_date = start_date_obj.strftime('%Y%m%d')
        end_date = target_date_obj.strftime('%Y%m%d')
        
        # 准备股票数据
        stock_data_dict = {}
        for symbol in symbols:
            df = self.data_handler.get_stock_data(symbol, start_date, end_date)
            if df is not None and len(df) > 20 and target_date in df.index.astype(str):
                stock_data_dict[symbol] = df
        
        if self.verbose:        
            print(f"成功获取 {len(stock_data_dict)} 只股票的有效数据")
            
        self.stock_data_dict = stock_data_dict
        return stock_data_dict
    
    def filter_stocks(self, 
                     strategy: B1Strategy, 
                     target_date: str,
                     return_details: bool = True) -> Dict[str, Any]:
        """
        过滤股票
        :param strategy: B1策略实例
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :param return_details: 是否返回详细信息
        :return: 包含筛选结果的字典
        """
        if not self.stock_data_dict:
            raise ValueError("请先调用load_stock_data加载股票数据")
            
        # 获取特定日期筛选结果
        filtered_results = strategy.get_filtered_stocks_by_date(
            self.stock_data_dict, 
            target_date,
            return_details=return_details
        )
        
        return filtered_results
    
    def display_results(self, filtered_results: Dict[str, Any], target_date: str) -> None:
        """
        显示筛选结果
        :param filtered_results: 筛选结果字典
        :param target_date: 目标日期
        """
        if not self.verbose:
            return
            
        print(f"\n{target_date} 通过B1策略筛选的股票：共 {len(filtered_results)} 只")
        print("-" * 60)
        
        if filtered_results:
            # 创建表格显示结果
            print(f"{'股票代码':<12} {'股票名称':<15} {'当日价格':<10} {'止损价':<10} {'目标价':<10} {'满足条件数':<10}")
            print("-" * 80)
            
            for symbol, details in filtered_results.items():
                # 获取股票名称（如果有市场数据处理器的获取股票名称方法）
                try:
                    stock_name = self.data_handler.get_stock_name(symbol)
                except:
                    stock_name = "N/A"
                    
                print(f"{symbol:<12} {stock_name:<15} {details['price']:<10.2f} "
                      f"{details['stop_loss']:<10.2f} {details['target_price']:<10.2f} "
                      f"{len(details['conditions_met']):<10}")
        else:
            print("该日期没有股票通过B1策略筛选。")
            
    def save_results_to_csv(self, 
                           filtered_results: Dict[str, Any], 
                           target_date: str, 
                           strategy_name: str = "custom") -> str:
        """
        将筛选结果保存到CSV文件
        :param filtered_results: 筛选结果字典
        :param target_date: 目标日期
        :param strategy_name: 策略名称或变体
        :return: 保存的文件路径
        """
        # 创建results目录（如果不存在）
        if not os.path.exists('results'):
            os.makedirs('results')
            
        # 准备数据
        data = []
        for symbol, details in filtered_results.items():
            data.append({
                '股票代码': symbol,
                '日期': details['date'],
                '价格': details['price'],
                '止损价': details['stop_loss'],
                '目标价': details['target_price'],
                '满足条件': ','.join(details['conditions_met'])
            })
            
        # 创建DataFrame并保存
        if data:
            df = pd.DataFrame(data)
            filename = f"results/b1_filtered_stocks_{target_date.replace('-', '')}_{strategy_name}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            if self.verbose:
                print(f"\n筛选结果已保存至: {filename}")
            return filename
        
        return ""
    
    def run(self, 
            target_date: str, 
            stock_pool: str = "hs300", 
            symbols: Optional[List[str]] = None, 
            stock_count: int = -1, 
            strategy: Optional[B1Strategy] = None,
            strategy_variant: str = "default", 
            save_results: bool = True) -> Dict[str, Any]:
        """
        运行完整的筛选流程
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :param stock_pool: 股票池类型
        :param symbols: 自定义股票池列表
        :param stock_count: 获取的股票数量上限，-1表示使用全部股票不截取
        :param strategy: B1策略实例，如果为None则创建新实例
        :param strategy_variant: 策略变体，当strategy为None时使用
        :param save_results: 是否保存结果到CSV
        :return: 筛选结果
        """
        if self.verbose:
            print(f"查询 {target_date} 的B1策略筛选结果")
            print("=" * 60)
            
        # 准备股票池
        test_symbols = self.prepare_stock_pool(stock_pool, symbols, stock_count)
        
        # 加载股票数据
        stock_data_dict = self.load_stock_data(test_symbols, target_date)
        
        # 创建或使用策略实例
        if strategy is None:
            strategy = B1Strategy()
            configure_strategy_variant(strategy, strategy_variant)
            used_strategy_name = strategy_variant
        else:
            used_strategy_name = "custom"
        
        # 筛选股票
        filtered_results = self.filter_stocks(strategy, target_date)
        
        # 显示结果
        self.display_results(filtered_results, target_date)
        
        # 保存结果
        if save_results and filtered_results:
            self.save_results_to_csv(filtered_results, target_date, used_strategy_name)
        
        return filtered_results


def configure_strategy_variant(strategy, variant_name):
    """配置不同的策略变体"""
    if variant_name == "volume_surge":
        # 放量策略变体
        strategy.set_active_conditions({
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": True,
            "volume_shrink_condition": False,
            "macd_golden_cross": False
        })
        strategy.update_params({"volume_ratio": 1.5})
        strategy.set_combination_logic("AND")
        
    elif variant_name == "loose":
        # 宽松条件组合策略
        strategy.set_active_conditions({
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False
        })
        strategy.update_params({"j_threshold": -5})
        strategy.set_combination_logic("OR")
        
    elif variant_name == "weighted":
        # 加权组合策略
        strategy.set_active_conditions({
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": True,
            "volume_shrink_condition": False,
            "macd_golden_cross": False
        })
        strategy.set_condition_weights({
            "kdj_condition": 2.0,
            "bottom_pattern_condition": 1.0,
            "big_positive_condition": 1.5,
            "above_ma_condition": 1.0,
            "volume_surge_condition": 0.5
        })
        strategy.set_combination_logic("WEIGHTED")
        
    elif variant_name == "b1+": #只看J<0
        strategy.set_active_conditions({
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False
        })
        strategy.set_combination_logic("AND")
    else:  # default
        # 默认B1策略，只看J<0
        strategy.set_active_conditions({
            "kdj_condition": True,
            "bottom_pattern_condition": False,
            "big_positive_condition": False,
            "above_ma_condition": False,
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False
        })
        strategy.set_combination_logic("AND")
    
    return strategy


def main():
    parser = argparse.ArgumentParser(description='B1策略股票筛选工具')
    parser.add_argument('--date', type=str, required=True, help='查询日期，格式为YYYY-MM-DD')
    parser.add_argument('--stock_count', type=int, default=-1, help='测试股票数量，-1表示使用全部股票不截取')
    parser.add_argument('--strategy', type=str, default='default', 
                        choices=['default', 'volume_surge', 'loose', 'weighted', 'j_nega'],
                        help='策略变体')
    parser.add_argument('--stock_pool', type=str, default='hs300', 
                        choices=['hs300', 'zz500', 'all_a', 'main', 'custom'], 
                        help='股票池类型: hs300(沪深300), zz500(中证500), all_a(所有A股), main(沪深主板), custom(自定义)')
    parser.add_argument('--symbols_file', type=str, help='自定义股票池文件路径，每行一个股票代码')
    parser.add_argument('--no_save', action='store_true', help='不保存结果到CSV文件')
    parser.add_argument('--quiet', action='store_true', help='静默模式，不打印详细信息')
    parser.add_argument('--encoding', type=str, default='utf-8', help='自定义股票池文件编码，默认utf-8')
    args = parser.parse_args()
    
    # 禁用代理设置
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    # 处理自定义股票池
    custom_symbols = None
    if args.stock_pool == 'custom' and args.symbols_file:
        try:
            with open(args.symbols_file, 'r', encoding=args.encoding) as f:
                custom_symbols = [line.strip() for line in f if line.strip()]
            if not args.quiet:
                print(f"从文件加载了 {len(custom_symbols)} 只自定义股票")
        except UnicodeDecodeError:
            # 如果默认编码失败，尝试其他常用编码
            try:
                with open(args.symbols_file, 'r', encoding='gbk') as f:
                    custom_symbols = [line.strip() for line in f if line.strip()]
                if not args.quiet:
                    print(f"使用GBK编码从文件加载了 {len(custom_symbols)} 只自定义股票")
            except Exception as e:
                if not args.quiet:
                    print(f"读取自定义股票池文件失败: {e}")
                    print("将使用默认股票池(沪深300)")
                args.stock_pool = 'hs300'
        except Exception as e:
            if not args.quiet:
                print(f"读取自定义股票池文件失败: {e}")
                print("将使用默认股票池(沪深300)")
            args.stock_pool = 'hs300'
    
    # 创建筛选器实例并运行
    filter = B1StockFilter(verbose=not args.quiet)
    filter.run(
        target_date=args.date,
        stock_pool=args.stock_pool,
        symbols=custom_symbols,
        stock_count=args.stock_count,
        strategy_variant=args.strategy,
        save_results=not args.no_save
    )


if __name__ == "__main__":
    main()


# 示例用法:
# python filter/b1_stock_filter.py --date 2025-08-01 --strategy weighted --stock_pool hs300  # 使用沪深300全部股票
# python filter/b1_stock_filter.py --date 2025-08-01 --strategy default --stock_pool all_a --stock_count 100  # 从全部A股中随机选取100只
# python filter/b1_stock_filter.py --date 2025-08-01 --strategy default --stock_pool main  # 使用全部沪深主板股票
# python filter/b1_stock_filter.py --date 2025-08-01 --strategy default --stock_count -1  # -1表示使用全部股票（不截取）