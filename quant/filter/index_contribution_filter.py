#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import akshare as ak
import os
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union

from ..util.market_data_handler import MarketDataHandler


class IndexContributionFilter:
    """
    指数贡献选股策略类
    用于获取各个板块的权重股，并筛选出KDJ<15的股票
    """
    
    def __init__(self, 
                 data_handler: Optional[MarketDataHandler] = None,
                 history_days: int = 45,
                 verbose: bool = True):
        """
        初始化指数贡献筛选器
        :param data_handler: 市场数据处理器实例，如果为None则创建新实例
        :param history_days: 获取历史数据的天数，默认45天
        :param verbose: 是否打印详细信息
        """
        self.data_handler = data_handler if data_handler else MarketDataHandler()
        self.history_days = history_days
        self.verbose = verbose
        self.sectors_data = {}  # 缓存板块数据
        self.stock_data_dict = {}  # 缓存股票数据
        
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
        :return: 板块数据字典 {sector_type: [sector_info]}
        """
        original_http_proxy, original_https_proxy = self._disable_proxies()
        
        try:
            all_sectors = {}
            
            if self.verbose:
                print("正在获取板块信息...")
            
            # 获取概念板块
            try:
                concept_df = ak.stock_board_concept_name_em()
                concept_list = []
                for _, row in concept_df.iterrows():
                    concept_list.append({
                        'code': row['板块代码'],
                        'name': row['板块名称'],
                        'stock_count': row.get('成分股数量', 0),
                        'type': '概念板块'
                    })
                all_sectors['concept'] = concept_list
                if self.verbose:
                    print(f"获取概念板块 {len(concept_list)} 个")
            except Exception as e:
                if self.verbose:
                    print(f"获取概念板块失败: {e}")
                all_sectors['concept'] = []
            
            # 获取行业板块  
            try:
                industry_df = ak.stock_board_industry_name_em()
                industry_list = []
                for _, row in industry_df.iterrows():
                    industry_list.append({
                        'code': row['板块代码'],
                        'name': row['板块名称'],
                        'stock_count': row.get('成分股数量', 0),
                        'type': '行业板块'
                    })
                all_sectors['industry'] = industry_list
                if self.verbose:
                    print(f"获取行业板块 {len(industry_list)} 个")
            except Exception as e:
                if self.verbose:
                    print(f"获取行业板块失败: {e}")
                all_sectors['industry'] = []
            
            # 获取地域板块
            try:
                region_df = ak.stock_board_cons_name_em()  # 地域板块
                region_list = []
                for _, row in region_df.iterrows():
                    if '地域' in str(row.get('板块名称', '')):
                        region_list.append({
                            'code': row['板块代码'],
                            'name': row['板块名称'],
                            'stock_count': row.get('成分股数量', 0),
                            'type': '地域板块'
                        })
                all_sectors['region'] = region_list
                if self.verbose:
                    print(f"获取地域板块 {len(region_list)} 个")
            except Exception as e:
                if self.verbose:
                    print(f"获取地域板块失败: {e}")
                all_sectors['region'] = []
            
            self.sectors_data = all_sectors
            return all_sectors
            
        except Exception as e:
            if self.verbose:
                print(f"获取板块数据失败: {e}")
            return {}
        finally:
            self._restore_proxies(original_http_proxy, original_https_proxy)
    
    def get_sector_stocks(self, sector_code: str, sector_type: str = 'concept') -> pd.DataFrame:
        """
        获取特定板块的成分股
        :param sector_code: 板块代码
        :param sector_type: 板块类型 ('concept', 'industry', 'region')
        :return: 成分股DataFrame
        """
        original_http_proxy, original_https_proxy = self._disable_proxies()
        
        try:
            if sector_type == 'concept':
                df = ak.stock_board_concept_cons_em(symbol=sector_code)
            elif sector_type == 'industry':
                df = ak.stock_board_industry_cons_em(symbol=sector_code)
            else:
                # 地域板块或其他
                df = ak.stock_board_cons_em(symbol=sector_code)
            
            # 数据清洗
            if '代码' in df.columns:
                df = df.rename(columns={'代码': 'stock_code'})
            elif '股票代码' in df.columns:
                df = df.rename(columns={'股票代码': 'stock_code'})
            
            if '名称' in df.columns:
                df = df.rename(columns={'名称': 'stock_name'})
            elif '股票名称' in df.columns:
                df = df.rename(columns={'股票名称': 'stock_name'})
            
            # 添加市值等信息
            if '总市值' in df.columns:
                df['market_cap'] = pd.to_numeric(df['总市值'], errors='coerce')
            elif '市值' in df.columns:
                df['market_cap'] = pd.to_numeric(df['市值'], errors='coerce')
            else:
                df['market_cap'] = 0
                
            return df
            
        except Exception as e:
            if self.verbose:
                print(f"获取板块 {sector_code} 成分股失败: {e}")
            return pd.DataFrame()
        finally:
            self._restore_proxies(original_http_proxy, original_https_proxy)
    
    def get_top_stocks_by_market_cap(self, sector_code: str, sector_type: str = 'concept', top_n: int = 10) -> pd.DataFrame:
        """
        获取板块中市值前N的权重股
        :param sector_code: 板块代码
        :param sector_type: 板块类型
        :param top_n: 取前N只股票，默认10只
        :return: 权重股DataFrame
        """
        df = self.get_sector_stocks(sector_code, sector_type)
        
        if df.empty:
            return df
        
        # 按市值排序，取前N只
        if 'market_cap' in df.columns:
            df_sorted = df.sort_values('market_cap', ascending=False)
        else:
            # 如果没有市值信息，尝试获取实时市值信息
            df_sorted = self._enrich_with_market_cap(df)
        
        top_stocks = df_sorted.head(top_n)
        
        if self.verbose:
            print(f"板块 {sector_code} 中市值前 {len(top_stocks)} 只权重股:")
            for _, row in top_stocks.iterrows():
                market_cap = row.get('market_cap', 0)
                if market_cap > 0:
                    market_cap_str = f"{market_cap/100000000:.1f}亿" if market_cap > 100000000 else f"{market_cap/10000:.1f}万"
                    print(f"  {row['stock_code']} {row.get('stock_name', 'N/A')} (市值: {market_cap_str})")
                else:
                    print(f"  {row['stock_code']} {row.get('stock_name', 'N/A')}")
        
        return top_stocks
    
    def _enrich_with_market_cap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        为股票数据补充市值信息
        :param df: 股票DataFrame
        :return: 带市值信息的DataFrame
        """
        original_http_proxy, original_https_proxy = self._disable_proxies()
        
        try:
            # 获取实时行情数据来计算市值
            for idx, row in df.iterrows():
                try:
                    stock_code = row['stock_code']
                    # 获取股票实时信息
                    stock_info = ak.stock_individual_info_em(symbol=stock_code)
                    if not stock_info.empty:
                        # 查找总市值
                        market_cap_row = stock_info[stock_info['item'] == '总市值']
                        if not market_cap_row.empty:
                            market_cap = pd.to_numeric(market_cap_row['value'].iloc[0], errors='coerce')
                            df.at[idx, 'market_cap'] = market_cap if not pd.isna(market_cap) else 0
                        else:
                            df.at[idx, 'market_cap'] = 0
                    else:
                        df.at[idx, 'market_cap'] = 0
                except:
                    df.at[idx, 'market_cap'] = 0
            
            return df.sort_values('market_cap', ascending=False)
            
        except Exception as e:
            if self.verbose:
                print(f"补充市值信息失败: {e}")
            return df
        finally:
            self._restore_proxies(original_http_proxy, original_https_proxy)
    
    def get_stock_kdj_info(self, stock_codes: List[str], target_date: str) -> Dict[str, Dict]:
        """
        获取股票的KDJ指标信息
        :param stock_codes: 股票代码列表
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :return: 股票KDJ信息字典
        """
        # 计算开始日期（往前推指定天数以获取足够的历史数据）
        target_date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        start_date_obj = target_date_obj - timedelta(days=self.history_days)
        start_date = start_date_obj.strftime('%Y%m%d')
        end_date = target_date_obj.strftime('%Y%m%d')
        
        kdj_info = {}
        
        for stock_code in stock_codes:
            try:
                # 获取股票历史数据
                df = self.data_handler.get_stock_data(stock_code, start_date, end_date)
                
                if df is not None and len(df) > 0 and target_date in df.index.astype(str):
                    target_row = df.loc[target_date]
                    
                    kdj_info[stock_code] = {
                        'date': target_date,
                        'close_price': target_row['close'],
                        'K': target_row.get('K', None),
                        'D': target_row.get('D', None),
                        'J': target_row.get('J', None),
                        'volume': target_row['volume'],
                        'pct_change': target_row.get('pct_change', 0)
                    }
                else:
                    if self.verbose:
                        print(f"无法获取股票 {stock_code} 在 {target_date} 的数据")
                    
            except Exception as e:
                if self.verbose:
                    print(f"获取股票 {stock_code} KDJ信息失败: {e}")
        
        return kdj_info
    
    def filter_kdj_stocks(self, kdj_info: Dict[str, Dict], kdj_threshold: float = 15.0) -> Dict[str, Dict]:
        """
        筛选KDJ指标小于阈值的股票
        :param kdj_info: 股票KDJ信息字典
        :param kdj_threshold: KDJ阈值，默认15
        :return: 筛选后的股票信息
        """
        filtered_stocks = {}
        
        for stock_code, info in kdj_info.items():
            j_value = info.get('J')
            if j_value is not None and j_value < kdj_threshold:
                filtered_stocks[stock_code] = info
        
        return filtered_stocks
    
    def display_sectors(self, sectors_data: Dict[str, List[Dict]]) -> None:
        """
        显示所有板块信息
        :param sectors_data: 板块数据字典
        """
        if not self.verbose:
            return
        
        print("\n================ 板块列表 ================")
        
        for sector_type, sectors in sectors_data.items():
            type_name = {
                'concept': '概念板块',
                'industry': '行业板块', 
                'region': '地域板块'
            }.get(sector_type, sector_type)
            
            print(f"\n{type_name} (共 {len(sectors)} 个):")
            print("-" * 50)
            
            for i, sector in enumerate(sectors[:20]):  # 只显示前20个
                print(f"{i+1:2d}. {sector['code']} - {sector['name']} (成分股: {sector.get('stock_count', 'N/A')})")
            
            if len(sectors) > 20:
                print(f"... 还有 {len(sectors) - 20} 个板块")
    
    def display_filtered_results(self, filtered_stocks: Dict[str, Dict], stock_names: Dict[str, str] = None) -> None:
        """
        显示筛选结果
        :param filtered_stocks: 筛选后的股票信息
        :param stock_names: 股票名称字典
        """
        if not self.verbose:
            return
        
        print(f"\n================ KDJ筛选结果 ================")
        print(f"共筛选出 {len(filtered_stocks)} 只股票 (J值 < 15):")
        print("-" * 80)
        
        if filtered_stocks:
            print(f"{'股票代码':<12} {'股票名称':<15} {'收盘价':<10} {'J值':<8} {'K值':<8} {'D值':<8} {'涨跌幅%':<10}")
            print("-" * 80)
            
            # 按J值排序
            sorted_stocks = sorted(filtered_stocks.items(), key=lambda x: x[1].get('J', 999))
            
            for stock_code, info in sorted_stocks:
                stock_name = stock_names.get(stock_code, 'N/A') if stock_names else 'N/A'
                
                print(f"{stock_code:<12} {stock_name:<15} "
                      f"{info['close_price']:<10.2f} "
                      f"{info.get('J', 'N/A'):<8.2f} "
                      f"{info.get('K', 'N/A'):<8.2f} "
                      f"{info.get('D', 'N/A'):<8.2f} "
                      f"{info.get('pct_change', 0):<10.2f}")
        else:
            print("没有股票符合筛选条件。")
    
    def save_results_to_csv(self, 
                           filtered_stocks: Dict[str, Dict], 
                           target_date: str,
                           sector_info: str = "",
                           stock_names: Dict[str, str] = None) -> str:
        """
        将筛选结果保存到CSV文件
        :param filtered_stocks: 筛选结果字典
        :param target_date: 目标日期
        :param sector_info: 板块信息
        :param stock_names: 股票名称字典
        :return: 保存的文件路径
        """
        # 创建results目录（如果不存在）
        if not os.path.exists('results'):
            os.makedirs('results')
        
        # 准备数据
        data = []
        for stock_code, info in filtered_stocks.items():
            stock_name = stock_names.get(stock_code, 'N/A') if stock_names else 'N/A'
            data.append({
                '股票代码': stock_code,
                '股票名称': stock_name,
                '日期': info['date'],
                '收盘价': info['close_price'],
                'J值': info.get('J', None),
                'K值': info.get('K', None),
                'D值': info.get('D', None),
                '涨跌幅%': info.get('pct_change', 0),
                '成交量': info['volume'],
                '板块信息': sector_info
            })
        
        # 创建DataFrame并保存
        if data:
            df = pd.DataFrame(data)
            filename = f"results/index_contribution_filtered_{target_date.replace('-', '')}_{sector_info.replace(' ', '_')}.csv"
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            if self.verbose:
                print(f"\n筛选结果已保存至: {filename}")
            return filename
        
        return ""
    
    def run(self,
            target_date: str,
            sector_codes: Optional[List[str]] = None,
            sector_type: str = 'concept',
            top_n: int = 10,
            kdj_threshold: float = 15.0,
            save_results: bool = True) -> Dict[str, Any]:
        """
        运行完整的指数贡献筛选流程
        :param target_date: 目标日期，格式为 'YYYY-MM-DD'
        :param sector_codes: 指定的板块代码列表，如果为None则显示所有板块供选择
        :param sector_type: 板块类型 ('concept', 'industry', 'region')
        :param top_n: 每个板块取市值前N只股票，默认10只
        :param kdj_threshold: KDJ阈值，默认15
        :param save_results: 是否保存结果到CSV
        :return: 筛选结果
        """
        if self.verbose:
            print(f"运行指数贡献选股策略 - {target_date}")
            print("=" * 60)
        
        # 获取所有板块信息
        all_sectors = self.get_all_sectors()
        
        if not sector_codes:
            # 显示所有板块供用户选择
            self.display_sectors(all_sectors)
            return {"sectors": all_sectors, "filtered_stocks": {}}
        
        # 处理指定的板块
        all_filtered_stocks = {}
        stock_names = {}
        
        for sector_code in sector_codes:
            if self.verbose:
                print(f"\n处理板块: {sector_code}")
                print("-" * 40)
            
            # 获取板块权重股
            top_stocks = self.get_top_stocks_by_market_cap(sector_code, sector_type, top_n)
            
            if top_stocks.empty:
                if self.verbose:
                    print(f"板块 {sector_code} 没有找到成分股")
                continue
            
            # 收集股票名称
            for _, row in top_stocks.iterrows():
                stock_names[row['stock_code']] = row.get('stock_name', 'N/A')
            
            # 获取股票KDJ信息
            stock_codes = top_stocks['stock_code'].tolist()
            kdj_info = self.get_stock_kdj_info(stock_codes, target_date)
            
            # 筛选KDJ < threshold的股票
            filtered_stocks = self.filter_kdj_stocks(kdj_info, kdj_threshold)
            
            # 合并结果
            all_filtered_stocks.update(filtered_stocks)
        
        # 显示结果
        self.display_filtered_results(all_filtered_stocks, stock_names)
        
        # 保存结果
        if save_results and all_filtered_stocks:
            sector_info = "_".join(sector_codes) if len(sector_codes) <= 3 else f"{len(sector_codes)}_sectors"
            self.save_results_to_csv(all_filtered_stocks, target_date, sector_info, stock_names)
        
        return {
            "sectors": all_sectors,
            "filtered_stocks": all_filtered_stocks,
            "stock_names": stock_names
        }


def main():
    parser = argparse.ArgumentParser(description='指数贡献选股策略工具')
    parser.add_argument('--date', type=str, required=True, help='查询日期，格式为YYYY-MM-DD')
    parser.add_argument('--sectors', type=str, nargs='*', help='指定板块代码，多个用空格分隔')
    parser.add_argument('--sector_type', type=str, default='concept', 
                        choices=['concept', 'industry', 'region'],
                        help='板块类型: concept(概念), industry(行业), region(地域)')
    parser.add_argument('--top_n', type=int, default=10, help='每个板块取市值前N只股票，默认10只')
    parser.add_argument('--kdj_threshold', type=float, default=15.0, help='KDJ阈值，默认15')
    parser.add_argument('--no_save', action='store_true', help='不保存结果到CSV文件')
    parser.add_argument('--quiet', action='store_true', help='静默模式，不打印详细信息')
    parser.add_argument('--list_sectors', action='store_true', help='只列出所有板块，不进行筛选')
    
    args = parser.parse_args()
    
    # 禁用代理设置
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''
    os.environ['http_proxy'] = ''
    os.environ['https_proxy'] = ''
    
    # 创建筛选器实例
    filter = IndexContributionFilter(verbose=not args.quiet)
    
    # 如果只是列出板块
    if args.list_sectors:
        sectors = filter.get_all_sectors()
        filter.display_sectors(sectors)
        return
    
    # 运行筛选流程
    filter.run(
        target_date=args.date,
        sector_codes=args.sectors,
        sector_type=args.sector_type,
        top_n=args.top_n,
        kdj_threshold=args.kdj_threshold,
        save_results=not args.no_save
    )


if __name__ == "__main__":
    main()


# 示例用法:
# python filter/index_contribution_filter.py --date 2025-08-01 --list_sectors  # 列出所有板块
# python filter/index_contribution_filter.py --date 2025-08-01 --sectors BK0447 BK0478  # 筛选指定概念板块
# python filter/index_contribution_filter.py --date 2025-08-01 --sectors BK0447 --sector_type industry --top_n 5  # 筛选行业板块前5只
# python filter/index_contribution_filter.py --date 2025-08-01 --sectors BK0447 --kdj_threshold 10  # 使用更严格的KDJ阈值
