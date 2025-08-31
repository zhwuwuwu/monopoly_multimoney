import pandas as pd
import numpy as np
import akshare as ak
import os
from datetime import datetime, timedelta


class MarketDataHandler:
    """
    市场数据处理类，负责获取和处理市场数据
    """
    def __init__(self):
        # 缓存数据
        self.hs300_components = None
        self.zz500_components = None
        self.all_stocks = None
        self.main_board_stocks = None
        self.historical_data = {}

    def _disable_proxies(self):
        """临时禁用代理设置"""
        # 保存原始代理设置
        original_http_proxy = os.environ.get('HTTP_PROXY', '')
        original_https_proxy = os.environ.get('HTTPS_PROXY', '')

        # 临时禁用代理
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

    def get_hs300_components(self):
        """获取沪深300成分股"""
        if self.hs300_components is None:
            # 保存并禁用代理设置
            original_http_proxy, original_https_proxy = self._disable_proxies()

            try:
                # 尝试使用akshare获取最新沪深300成分股
                print("正在从akshare获取沪深300成分股...")
                df = ak.index_stock_cons_sina(symbol="000300")
                self.hs300_components = df['code'].tolist()
                print(f"获取沪深300成分股 {len(self.hs300_components)} 只")
            except Exception as e:
                print(f"从新浪财经获取沪深300成分股失败: {str(e)}")
                print("使用本地备选股票列表...")

                # 备选方案：使用硬编码的沪深300成分股列表（可能不是最新的）
                self.hs300_components = [
                    '600519', '601318', '600036', '601166', '000333',
                    '000858', '601888', '600276', '601398', '600030',
                    '600887', '601288', '000651', '000001', '600000',
                    '601668', '002415', '600900', '601628', '002475',
                    '601857', '600031', '601988', '601601', '600028',
                    '601899', '600309', '000725', '601088', '600050'
                ]
                print(f"使用本地备选股票列表 {len(self.hs300_components)} 只")
            finally:
                # 恢复原始代理设置
                self._restore_proxies(original_http_proxy, original_https_proxy)

        return self.hs300_components

    def get_zz500_components(self):
        """获取中证500成分股"""
        if self.zz500_components is None:
            # 保存并禁用代理设置
            original_http_proxy, original_https_proxy = self._disable_proxies()

            try:
                # 尝试使用akshare获取最新中证500成分股
                print("正在从akshare获取中证500成分股...")
                df = ak.index_stock_cons_sina(symbol="000905")
                self.zz500_components = df['code'].tolist()
                print(f"获取中证500成分股 {len(self.zz500_components)} 只")
            except Exception as e:
                print(f"从新浪财经获取中证500成分股失败: {str(e)}")
                print("使用本地备选股票列表或沪深300成分股替代...")
                self.zz500_components = self.get_hs300_components()
            finally:
                # 恢复原始代理设置
                self._restore_proxies(original_http_proxy, original_https_proxy)

        return self.zz500_components

    def get_all_a_stocks(self):
        """获取所有A股上市股票"""
        if self.all_stocks is None:
            # 保存并禁用代理设置
            original_http_proxy, original_https_proxy = self._disable_proxies()

            try:
                print("正在从akshare获取所有A股上市股票...")
                # 获取所有A股股票
                df = ak.stock_info_a_code_name()
                self.all_stocks = df['code'].tolist()
                print(f"获取全部A股上市股票 {len(self.all_stocks)} 只")
            except Exception as e:
                print(f"获取所有A股上市股票失败: {str(e)}")
                print("使用沪深300成分股替代...")
                self.all_stocks = self.get_hs300_components()
            finally:
                # 恢复原始代理设置
                self._restore_proxies(original_http_proxy, original_https_proxy)

        return self.all_stocks

    def get_main_board_stocks(self):
        """获取沪深主板股票（排除创业板、科创板等）"""
        if self.main_board_stocks is None:
            all_stocks = self.get_all_a_stocks()
            # 筛选主板股票（沪市主板以60开头，深市主板以00开头）
            self.main_board_stocks = [s for s in all_stocks if s.startswith(('600', '601', '603', '605', '000'))]
            print(f"筛选沪深主板股票 {len(self.main_board_stocks)} 只")

        return self.main_board_stocks

    def get_stock_data(self, symbol, start_date, end_date):
        """获取股票历史数据"""
        # 检查缓存
        cache_key = f"{symbol}_{start_date}_{end_date}"
        if cache_key in self.historical_data:
            return self.historical_data[cache_key]

        # 确保网络请求不使用代理
        original_http_proxy = os.environ.get('HTTP_PROXY', '')
        original_https_proxy = os.environ.get('HTTPS_PROXY', '')

        try:
            # 临时禁用代理
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''

            # 使用akshare获取数据
            # 转换日期格式
            start_date_fmt = pd.to_datetime(start_date).strftime('%Y%m%d')
            end_date_fmt = pd.to_datetime(end_date).strftime('%Y%m%d')

            # 根据股票代码前两位数字推断交易所信息
            if symbol.startswith('6'):
                exchange = 'SH'
            elif symbol.startswith('0') or symbol.startswith('3'):
                exchange = 'SZ'
            else:
                raise ValueError(f"无法确定股票 {symbol} 的交易所")

            # 获取股票历史数据 - akshare只需要纯数字代码
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", 
                                   start_date=start_date_fmt, end_date=end_date_fmt, 
                                   adjust="qfq")

            # 数据清洗和处理
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.rename(columns={
                '日期': 'trade_date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })
            df.set_index('trade_date', inplace=True)

            # 计算KDJ指标
            df = self.calculate_kdj(df)

            # 缓存数据
            self.historical_data[cache_key] = df
            return df
        except Exception as e:
            print(f"获取数据失败: {symbol}, 错误: {str(e)}")
            return None
        finally:
            # 恢复原始代理设置
            if original_http_proxy:
                os.environ['HTTP_PROXY'] = original_http_proxy
            if original_https_proxy:
                os.environ['HTTPS_PROXY'] = original_https_proxy

    def get_index_data(self, index_symbol, start_date, end_date):
        """
        获取指数历史数据
        :param index_symbol: 指数代码，如'000300'表示沪深300
        :param start_date: 开始日期
        :param end_date: 结束日期
        :return: 指数历史数据DataFrame
        """
        # 检查缓存
        cache_key = f"index_{index_symbol}_{start_date}_{end_date}"
        if hasattr(self, 'index_data') and cache_key in self.index_data:
            return self.index_data[cache_key]

        # 初始缓存字典（如果不存在）
        if not hasattr(self, 'index_data'):
            self.index_data = {}

        # 确保网络请求不使用代理
        original_http_proxy = os.environ.get('HTTP_PROXY', '')
        original_https_proxy = os.environ.get('HTTPS_PROXY', '')

        try:
            # 临时禁用代理
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''
            os.environ['http_proxy'] = ''
            os.environ['https_proxy'] = ''

            # 转换日期格式
            start_date_fmt = pd.to_datetime(start_date).strftime('%Y%m%d')
            end_date_fmt = pd.to_datetime(end_date).strftime('%Y%m%d')

            # 判断指数类型，获取相应数据
            if index_symbol in ['000300', '000001']:
                df = ak.stock_zh_index_daily(symbol="sh" + index_symbol)
            elif index_symbol in ['399001', '399006']:
                df = ak.stock_zh_index_daily(symbol="sz" + index_symbol)
            else:
                try:
                    df = ak.stock_zh_index_daily(symbol="sh" + index_symbol)
                except:
                    df = ak.stock_zh_index_daily(symbol="sz" + index_symbol)

            # 数据清洗和处理
            df['date'] = pd.to_datetime(df['date'])
            df = df.rename(columns={
                'date': 'trade_date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            df = df[(df['trade_date'] >= pd.to_datetime(start_date)) & (df['trade_date'] <= pd.to_datetime(end_date))]
            df.set_index('trade_date', inplace=True)

            # 缓存数据
            self.index_data[cache_key] = df
            return df

        except Exception as e:
            print(f"获取指数数据失败: {index_symbol}, 错误: {str(e)}")
            return None
        finally:
            # 恢复原始代理设置
            if original_http_proxy:
                os.environ['HTTP_PROXY'] = original_http_proxy
            if original_https_proxy:
                os.environ['HTTPS_PROXY'] = original_https_proxy

    def calculate_kdj(self, df, n=9, m1=3, m2=3):
        """计算KDJ指标，同时使用两种方法"""
        low_min = df['low'].rolling(window=n).min()
        high_max = df['high'].rolling(window=n).max()

        # 方法1: 传统方法，使用ewm
        rsv1 = (df['close'] - low_min) / (high_max - low_min) * 100
        rsv1.fillna(50, inplace=True)

        df['K'] = rsv1.ewm(alpha=1 / m1, adjust=False).mean()
        df['D'] = df['K'].ewm(alpha=1 / m2, adjust=False).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']

        return df
