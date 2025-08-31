#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import akshare as ak
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

from ..util.market_data_handler import MarketDataHandler


class IndexContributionFilter:
    """
    指数贡献选股策略类
    用于获取各板块的权重股并筛选KDJ<15的股票
    """
    
    def __init__(self, 
                 data_handler: Optional[MarketDataHandler] = None,
                 history_days: int = 60,
                 verbose: bool = True):
        """
        初始化指数贡献筛选器
        :param data_handler: 市场数据处理器实例，如果为None则创建新实例
        :param history_days: 获取历史数据的天数，默认60天
        :param verbose: 是否打印详细信息
        """
        self.data_handler = data_handler if data_handler else MarketDataHandler()
        self.history_days = history_days
        self.verbose = verbose
        self.sector_data = {}  # 缓存板块数据
        self.stock_data = {}   # 缓存股票数据
        
    def _disable_proxies(self):
        """临时禁用代理设置"""
        original_http_proxy = os.environ.get('HTTP_PROXY', '')
        original_https_proxy = os.environ.get('HTTPS_PROXY', '')
        
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''
        os.environ['http_proxy'] = ''
        os.environ['https_proxy'] = ''
        
        return original_http_proxy, original_https_proxy
    
    def _restore_proxies(self, original_http_proxy, original_https_proxy):
        """恢复原始代理设置"""
        if original_http_proxy:
            os.environ['HTTP_PROXY'] = original_http_proxy
        if original_https_proxy:
            os.environ['HTTPS_PROXY'] = original_https_proxy
    
    def get_all_sectors(self) -> Dict[str, List[Dict]]:
        """
        获取沪深市场所有板块列表
        :return: 板块字典 {'sector_name': [{'code': 'xxx', 'name': 'xxx'}, ...]}
        """
        original_http_proxy, original_https_proxy = self._disable_proxies()
        
        try:
            if self.verbose:
                print("正在获取所有板块信息...")
            
            sectors = {}
            
            # 获取概念板块
            if self.verbose:
                print("获取概念板块...")
            try:
                concept_df = ak.stock_board_concept_name_em()
                if not concept_df.empty:
                    sectors['概念板块'] = [
                        {'code': row['板块代码'], 'name': row['板块名称']} 
                        for _, row in concept_df.iterrows()
                    ]
                    if self.verbose:
                        print(f"获取到 {len(sectors['概念板块'])} 个概念板块")
            except Exception as e:
                if self.verbose:
                    print(f"获取概念板块失败: {e}")
                sectors['概念板块'] = []
            
            # 获取行业板块  
            if self.verbose:
                print("获取行业板块...")
            try:
                industry_df = ak.stock_board_industry_name_em()
                if not industry_df.empty:
                    sectors['行业板块'] = [
                        {'code': row['板块代码'], 'name': row['板块名称']} 
                        for _, row in industry_df.iterrows()
                    ]
                    if self.verbose:
                        print(f"获取到 {len(sectors['行业板块'])} 个行业板块")
            except Exception as e:
                if self.verbose:
                    print(f"获取行业板块失败: {e}")
                sectors['行业板块'] = []
            
            # 获取地域板块
            if self.verbose:
                print("获取地域板块...")
            try:
                area_df = ak.stock_board_area_name_em()
                if not area_df.empty:
                    sectors['地域板块'] = [
                        {'code': row['板块代码'], 'name': row['板块名称']} 
                        for _, row in area_df.iterrows()
                    ]
                    if self.verbose:
                        print(f"获取到 {len(sectors['地域板块'])} 个地域板块")
            except Exception as e:
                if self.verbose:
                    print(f"获取地域板块失败: {e}")
                sectors['地域板块'] = []
            
            return sectors
            
        except Exception as e:
            if self.verbose:
                print(f"获取板块列表失败: {e}")
            return {}
        finally:
            self._restore_proxies(original_http_proxy, original_https_proxy)
    
    def display_sectors(self, sectors: Dict[str, List[Dict]]) -> None:
        """
        显示可选择的板块列表
        :param sectors: 板块字典
        """
        if not self.verbose:
            return
            
        print("\n可选择的板块类型:")
        print("=" * 50)
        
        for sector_type, sector_list in sectors.items():
            print(f"\n{sector_type} (共{len(sector_list)}个):")
            print("-" * 40)
            
            # 显示前10个作为示例
            for i, sector in enumerate(sector_list[:10]):
                print(f"  {i+1:2d}. {sector['name']} ({sector['code']})")
            
            if len(sector_list) > 10:
                print(f"  ... 还有 {len(sector_list) - 10} 个板块")
    
    def get_sector_stocks(self, sector_code: str, sector_type: str = "概念板块") -> pd.DataFrame:
        """
        获取指定板块的成分股
        :param sector_code: 板块代码
        :param sector_type: 板块类型
        :return: 成分股DataFrame
        """
        original_http_proxy, original_https_proxy = self._disable_proxies()
        
        try:
            if self.verbose:
                print(f"正在获取板块 {sector_code} 的成分股...")
            
            # 根据板块类型选择相应的API
            if sector_type == "概念板块":
                df = ak.stock_board_concept_cons_em(symbol=sector_code)
            elif sector_type == "行业板块":
                df = ak.stock_board_industry_cons_em(symbol=sector_code)
            elif sector_type == "地域板块":
                df = ak.stock_board_area_cons_em(symbol=sector_code)
            else:
                raise ValueError(f"不支持的板块类型: {sector_type}")
            
            if df is not None and not df.empty:
                # 确保包含必要的列
                required_columns = ['代码', '名称', '最新价', '总市值']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    if self.verbose:
                        print(f"缺少列: {missing_columns}")
                    # 尝试使用可用的列
                    if '代码' in df.columns and '名称' in df.columns:
                        return df[['代码', '名称']].copy()
                else:
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            if self.verbose:
                print(f"获取板块成分股失败: {e}")
            return pd.DataFrame()
        finally:
            self._restore_proxies(original_http_proxy, original_https_proxy)
    
    def get_top_weight_stocks(self, sector_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        获取板块中市值前N的权重股
        :param sector_df: 板块成分股DataFrame
        :param top_n: 选取的股票数量
        :return: 权重股DataFrame
        """
        if sector_df.empty:
            return pd.DataFrame()
        
        # 如果有市值列，按市值排序
        if '总市值' in sector_df.columns:
            # 处理市值数据，可能包含单位（亿、万等）
            sector_df = sector_df.copy()
            market_cap = sector_df['总市值'].astype(str)
            
            # 转换市值为数值（假设单位为亿）
            numeric_market_cap = []
            for cap in market_cap:
                try:
                    if '亿' in cap:
                        numeric_market_cap.append(float(cap.replace('亿', '').replace(',', '')))
                    elif '万亿' in cap:
                        numeric_market_cap.append(float(cap.replace('万亿', '').replace(',', '')) * 10000)
                    else:
                        numeric_market_cap.append(float(cap.replace(',', '')))
                except:
                    numeric_market_cap.append(0)
            
            sector_df['市值_数值'] = numeric_market_cap
            top_stocks = sector_df.nlargest(top_n, '市值_数值')
        else:
            # 如果没有市值列，就取前N个
            top_stocks = sector_df.head(top_n)
        
        return top_stocks
    
    def calculate_kdj(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """
        计算KDJ指标
        :param df: 股票数据DataFrame (包含high, low, close列)
        :param n: RSV计算周期，默认9
        :param m1: K值平滑周期，默认3
        :param m2: D值平滑周期，默认3
        :return: 包含KDJ值的DataFrame
        """
        df = df.copy()
        
        # 计算RSV
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        
        # 计算K、D、J
        df['K'] = rsv.ewm(span=m1).mean()
        df['D'] = df['K'].ewm(span=m2).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']
        
        return df
    
    def filter_stocks_by_kdj(self, stocks_df: pd.DataFrame, target_date: str, kdj_threshold: float = 15) -> List[Dict]:
        """
        根据KDJ指标筛选股票
        :param stocks_df: 股票列表DataFrame
        :param target_date: 目标日期
        :param kdj_threshold: KDJ阈值，默认15
        :return: 符合条件的股票列表
        """
        if stocks_df.empty:
            return []
        
        filtered_stocks = []
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        start_date_obj = target_date_obj - timedelta(days=self.history_days)
        start_date = start_date_obj.strftime('%Y%m%d')
        end_date = target_date_obj.strftime('%Y%m%d')
        
        for _, stock in stocks_df.iterrows():
            symbol = stock['代码']
            name = stock['名称']
            
            try:
                # 获取股票历史数据
                stock_data = self.data_handler.get_stock_data(symbol, start_date, end_date)
                
                if stock_data is not None and len(stock_data) > 20:
                    # 计算KDJ
                    stock_data_with_kdj = self.calculate_kdj(stock_data)
                    
                    # 获取目标日期的KDJ值
                    target_data = stock_data_with_kdj[stock_data_with_kdj.index.astype(str) == target_date]
                    
                    if not target_data.empty:
                        j_value = target_data['J'].iloc[0]
                        k_value = target_data['K'].iloc[0]
                        d_value = target_data['D'].iloc[0]
                        current_price = target_data['close'].iloc[0]
                        
                        # 检查J值是否小于阈值
                        if j_value < kdj_threshold:
                            stock_info = {
                                'symbol': symbol,
                                'name': name,
                                'price': current_price,
                                'K': k_value,
                                'D': d_value,
                                'J': j_value,
                                'date': target_date
                            }
                            
                            # 如果原DataFrame包含市值信息，也加入
                            if '总市值' in stock.index:
                                stock_info['market_cap'] = stock['总市值']
                            if '市值_数值' in stock.index:
                                stock_info['market_cap_numeric'] = stock['市值_数值']
                                
                            filtered_stocks.append(stock_info)
                            
                            if self.verbose:
                                print(f"找到符合条件的股票: {symbol} {name}, J={j_value:.2f}")
                
            except Exception as e:
                if self.verbose:
                    print(f"处理股票 {symbol} 时出错: {e}")
                continue
        
        return filtered_stocks
    
    def display_filtered_results(self, filtered_stocks: List[Dict], sector_name: str) -> None:
        """
        显示筛选结果
        :param filtered_stocks: 筛选出的股票列表
        :param sector_name: 板块名称
        """
        if not self.verbose:
            return
            
        print(f"\n板块 [{sector_name}] KDJ<15 的股票筛选结果:")
        print("=" * 80)
        
        if filtered_stocks:
            print(f"{'股票代码':<10} {'股票名称':<15} {'当前价格':<10} {'K值':<8} {'D值':<8} {'J值':<8} {'市值':<12}")
            print("-" * 80)
            
            for stock in filtered_stocks:
                market_cap_str = stock.get('market_cap', 'N/A')
                print(f"{stock['symbol']:<10} {stock['name']:<15} {stock['price']:<10.2f} "
                      f"{stock['K']:<8.2f} {stock['D']:<8.2f} {stock['J']:<8.2f} {market_cap_str:<12}")
        else:
            print("该板块没有符合条件的股票。")
    
    def save_results_to_csv(self, filtered_stocks: List[Dict], sector_name: str, target_date: str) -> str:
        """
        将筛选结果保存到CSV文件
        :param filtered_stocks: 筛选出的股票列表
        :param sector_name: 板块名称
        :param target_date: 目标日期
        :return: 保存的文件路径
        """
        if not filtered_stocks:
            return ""
        
        # 创建results目录（如果不存在）
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 创建DataFrame
        df = pd.DataFrame(filtered_stocks)
        
        # 重新排列列的顺序
        columns_order = ['symbol', 'name', 'price', 'K', 'D', 'J', 'date']
        if 'market_cap' in df.columns:
            columns_order.append('market_cap')
        if 'market_cap_numeric' in df.columns:
            columns_order.append('market_cap_numeric')
        
        df = df[columns_order]
        
        # 保存文件
        filename = f"results/index_contribution_{sector_name.replace('/', '_')}_{target_date.replace('-', '')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        if self.verbose:
            print(f"\n筛选结果已保存至: {filename}")
        
        return filename
    
    def run(self, 
            target_date: str,
            sector_type: str = "概念板块",
            sector_name: Optional[str] = None,
            sector_code: Optional[str] = None, 
            top_n: int = 10,
            kdj_threshold: float = 15,
            save_results: bool = True) -> Dict[str, Any]:
        """
        运行指数贡献筛选策略
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :param sector_type: 板块类型 ('概念板块', '行业板块', '地域板块')
        :param sector_name: 板块名称
        :param sector_code: 板块代码
        :param top_n: 每个板块选取的权重股数量
        :param kdj_threshold: KDJ阈值
        :param save_results: 是否保存结果到CSV
        :return: 筛选结果
        """
        if self.verbose:
            print(f"指数贡献筛选策略 - 目标日期: {target_date}")
            print("=" * 60)
        
        # 1. 获取所有板块列表
        if sector_code is None:
            sectors = self.get_all_sectors()
            self.display_sectors(sectors)
            
            # 如果没有指定板块，返回板块列表供用户选择
            if sector_name is None:
                return {"sectors": sectors, "message": "请选择要分析的板块"}
        
        # 2. 获取指定板块的成分股
        if sector_code:
            sector_stocks = self.get_sector_stocks(sector_code, sector_type)
            used_sector_name = sector_name or sector_code
        else:
            return {"error": "请提供板块代码"}
        
        if sector_stocks.empty:
            return {"error": f"无法获取板块 {sector_code} 的成分股"}
        
        if self.verbose:
            print(f"\n板块 [{used_sector_name}] 共有 {len(sector_stocks)} 只成分股")
        
        # 3. 获取权重股（市值前N）
        top_stocks = self.get_top_weight_stocks(sector_stocks, top_n)
        
        if self.verbose:
            print(f"选取市值前 {len(top_stocks)} 只权重股进行分析")
        
        # 4. 显示权重股详细信息
        if self.verbose and not top_stocks.empty:
            print(f"\n权重股详细信息:")
            print("-" * 60)
            for i, (_, stock) in enumerate(top_stocks.iterrows(), 1):
                market_cap = stock.get('总市值', 'N/A')
                price = stock.get('最新价', 'N/A')
                print(f"{i:2d}. {stock['代码']} {stock['名称']:<15} 价格:{price} 市值:{market_cap}")
        
        # 5. 筛选KDJ<阈值的股票
        filtered_stocks = self.filter_stocks_by_kdj(top_stocks, target_date, kdj_threshold)
        
        # 显示结果
        self.display_filtered_results(filtered_stocks, used_sector_name)
        
        # 保存结果
        if save_results and filtered_stocks:
            self.save_results_to_csv(filtered_stocks, used_sector_name, target_date)
        
        return {
            "sector_name": used_sector_name,
            "sector_code": sector_code,
            "total_stocks": len(sector_stocks),
            "top_stocks": len(top_stocks),
            "filtered_stocks": filtered_stocks,
            "kdj_threshold": kdj_threshold
        }


def main():
    parser = argparse.ArgumentParser(description='指数贡献选股策略工具')
    parser.add_argument('--date', type=str, required=True, help='查询日期，格式为YYYY-MM-DD')
    parser.add_argument('--sector_type', type=str, default='概念板块', 
                        choices=['概念板块', '行业板块', '地域板块'],
                        help='板块类型')
    parser.add_argument('--sector_code', type=str, help='板块代码')
    parser.add_argument('--sector_name', type=str, help='板块名称')
    parser.add_argument('--top_n', type=int, default=10, help='每个板块选取的权重股数量')
    parser.add_argument('--kdj_threshold', type=float, default=15, help='KDJ阈值')
    parser.add_argument('--no_save', action='store_true', help='不保存结果到CSV文件')
    parser.add_argument('--quiet', action='store_true', help='静默模式，不打印详细信息')
    args = parser.parse_args()
    
    # 禁用代理设置
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    # 创建筛选器实例并运行
    filter = IndexContributionFilter(verbose=not args.quiet)
    result = filter.run(
        target_date=args.date,
        sector_type=args.sector_type,
        sector_name=args.sector_name,
        sector_code=args.sector_code,
        top_n=args.top_n,
        kdj_threshold=args.kdj_threshold,
        save_results=not args.no_save
    )
    
    if "sectors" in result:
        print("\n使用示例:")
        print("python filter/index_contribution_filter.py --date 2025-08-01 --sector_code BK0447 --sector_name 白酒概念")


if __name__ == "__main__":
    main()


# 示例用法:
# python filter/index_contribution_filter.py --date 2025-08-01 --sector_type 概念板块 --sector_code BK0447 --sector_name 白酒概念
# python filter/index_contribution_filter.py --date 2025-08-01 --sector_type 行业板块 --sector_code BK0464 --top_n 15
# python filter/index_contribution_filter.py --date 2025-08-01 --sector_type 地域板块 --sector_code BK0493 --kdj_threshold 10
