import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Callable, Union, Tuple, Optional, Any

class ConditionType(Enum):
    """条件类型枚举"""
    KDJ = "kdj"
    MACD = "macd"
    VOLUME = "volume"
    PRICE_PATTERN = "price_pattern"
    MOVING_AVERAGE = "moving_average"
    FUNDAMENTAL = "fundamental"
    CUSTOM = "custom"

class B1Strategy:
    """
    B1策略类，负责信号生成和策略逻辑
    重构版：使用模块化、可配置的条件组合
    """
    def __init__(self):
        # 策略基本参数
        self.params = {
            'kdj_threshold': 10,     # KDJ粗筛阈值
            'j_threshold': -10,      # J值精筛阈值
            'stop_loss_pct': 0.12,   # 止损比例
            'take_profit_pct': 0.3,  # 止盈比例
            'position_ratio': 0.2,   # 单笔仓位比例
            'min_trade_days': 20,    # 最小交易天数
            'max_hold_days': 30,     # 最大持有天数
            'ma_window': 20,         # 移动平均窗口大小
            'volume_ratio': 2.0,     # 量比阈值
            'big_positive_pct': 0.05 # 大阳线涨幅阈值
        }
        
        # 初始化条件函数字典
        self.condition_functions = self._init_condition_functions()
        
        # 默认使用的条件组合
        self.default_conditions = {
            "kdj_condition": True,         # KDJ条件
            "bottom_pattern_condition": True,  # 底分型条件
            "big_positive_condition": True,    # 大阳线条件
            "above_ma_condition": True,        # 均线之上条件
            # 其他条件默认关闭
            "volume_surge_condition": False,   # 放量条件
            "volume_shrink_condition": False,  # 缩量条件
            "macd_golden_cross": False,        # MACD金叉
        }
        
        # 设置当前激活的条件组合
        self.active_conditions = self.default_conditions.copy()
        
        # 条件组合逻辑，默认为"与"逻辑
        self.combination_logic = "AND"  # 可选 "AND", "OR", "WEIGHTED"
        
        # 条件权重，用于加权组合时
        self.condition_weights = {
            "kdj_condition": 1.0,
            "bottom_pattern_condition": 1.0,
            "big_positive_condition": 1.0,
            "above_ma_condition": 1.0,
            "volume_surge_condition": 0.5,
            "volume_shrink_condition": 0.5,
            "macd_golden_cross": 0.5,
        }
        
    def _init_condition_functions(self) -> Dict[str, Callable]:
        """初始化所有条件函数"""
        return {
            # KDJ相关条件
            "kdj_condition": self._check_kdj_condition,
            
            # 价格形态条件
            "bottom_pattern_condition": self._check_bottom_pattern,
            "big_positive_condition": self._check_big_positive,
            
            # 均线条件
            "above_ma_condition": self._check_above_ma,
            
            # 成交量条件
            "volume_surge_condition": self._check_volume_surge,
            "volume_shrink_condition": self._check_volume_shrink,
            
            # MACD条件
            "macd_golden_cross": self._check_macd_golden_cross,
        }
    
    # ------ 各种条件检查函数 ------
    
    def _check_kdj_condition(self, df, i) -> bool:
        """检查KDJ条件：J值低于阈值"""
        return df['J'].iloc[i] < self.params['j_threshold']
    
    def _check_bottom_pattern(self, df, i) -> bool:
        """检查底分型条件：中间K线的低点和高点都是三天内最低"""
        if i < 2:
            return False
        return (
            df['low'].iloc[i] < df['low'].iloc[i-1] and 
            df['low'].iloc[i] < df['low'].iloc[i-2] and
            df['high'].iloc[i] < df['high'].iloc[i-1] and
            df['high'].iloc[i] < df['high'].iloc[i-2]
        )
    
    def _check_big_positive(self, df, i) -> bool:
        """检查大阳线条件：涨幅超过阈值"""
        if i < 1:
            return False
        return df['close'].iloc[i] > df['open'].iloc[i] * (1 + self.params['big_positive_pct'])
    
    def _check_above_ma(self, df, i) -> bool:
        """检查是否在均线之上"""
        ma = df['close'].rolling(window=self.params['ma_window']).mean().iloc[i]
        return df['close'].iloc[i] > ma
    
    def _check_volume_surge(self, df, i) -> bool:
        """检查放量条件：成交量比前N日均量大"""
        if i < 5:
            return False
        avg_volume = df['volume'].iloc[i-5:i].mean()
        return df['volume'].iloc[i] > avg_volume * self.params['volume_ratio']
    
    def _check_volume_shrink(self, df, i) -> bool:
        """检查缩量条件：成交量比前N日均量小"""
        if i < 5:
            return False
        avg_volume = df['volume'].iloc[i-5:i].mean()
        return df['volume'].iloc[i] < avg_volume / self.params['volume_ratio']
    
    def _check_macd_golden_cross(self, df, i) -> bool:
        """检查MACD金叉：需要计算MACD"""
        if 'MACD' not in df.columns:
            return False
        if i < 1:
            return False
        return df['MACD'].iloc[i-1] < 0 and df['MACD'].iloc[i] > 0
    
    # ------ 条件组合逻辑 ------
    
    def _combine_conditions_and(self, df, i) -> bool:
        """使用"与"逻辑组合条件"""
        for condition_name, is_active in self.active_conditions.items():
            if is_active:
                if not self.condition_functions[condition_name](df, i):
                    return False
        return True
    
    def _combine_conditions_or(self, df, i) -> bool:
        """使用"或"逻辑组合条件"""
        for condition_name, is_active in self.active_conditions.items():
            if is_active:
                if self.condition_functions[condition_name](df, i):
                    return True
        return False
    
    def _combine_conditions_weighted(self, df, i) -> float:
        """使用加权方式组合条件，返回得分"""
        total_weight = 0
        total_score = 0
        
        for condition_name, is_active in self.active_conditions.items():
            if is_active:
                weight = self.condition_weights[condition_name]
                total_weight += weight
                if self.condition_functions[condition_name](df, i):
                    total_score += weight
        
        if total_weight == 0:
            return 0
        
        return total_score / total_weight
    
    def detect_b1_signal(self, df):
        """检测B1买入信号，使用配置的条件组合"""
        signals = []
        
        # 确保有足够的数据
        if len(df) < self.params['min_trade_days']:
            return signals
        
        # 检测B1信号
        for i in range(2, len(df)):
            signal_triggered = False
            
            if self.combination_logic == "AND":
                signal_triggered = self._combine_conditions_and(df, i)
            elif self.combination_logic == "OR":
                signal_triggered = self._combine_conditions_or(df, i)
            elif self.combination_logic == "WEIGHTED":
                score = self._combine_conditions_weighted(df, i)
                signal_triggered = score > 0.7
            
            if signal_triggered:
                signals.append({
                    'date': df.index[i],
                    'price': df['close'].iloc[i],
                    'stop_loss': df['low'].iloc[i-1] * (1 - self.params['stop_loss_pct']),
                    'target_price': df['close'].iloc[i] * (1 + self.params['take_profit_pct'])
                })
        
        return signals
    
    def set_active_conditions(self, conditions_dict):
        """
        设置要使用的条件
        :param conditions_dict: 字典 {条件名: 布尔值}
        """
        for condition_name, is_active in conditions_dict.items():
            if condition_name in self.condition_functions:
                self.active_conditions[condition_name] = is_active
            else:
                raise ValueError(f"未知的条件: {condition_name}")
        return self.active_conditions
    
    def set_combination_logic(self, logic):
        """
        设置条件组合逻辑
        :param logic: "AND", "OR" 或 "WEIGHTED"
        """
        if logic not in ["AND", "OR", "WEIGHTED"]:
            raise ValueError("无效的组合逻辑，必须是 AND, OR 或 WEIGHTED")
        self.combination_logic = logic
        return self.combination_logic
    
    def set_condition_weights(self, weights_dict):
        """
        设置条件权重
        :param weights_dict: 字典 {条件名: 权重}
        """
        for condition_name, weight in weights_dict.items():
            if condition_name in self.condition_functions:
                self.condition_weights[condition_name] = float(weight)
            else:
                raise ValueError(f"未知的条件: {condition_name}")
        return self.condition_weights
        
    def update_params(self, new_params):
        """更新策略参数"""
        self.params.update(new_params)
        return self.params

    def filter_stocks_by_kdj(self, stocks_data_dict, kdj_threshold=None):
        """
        使用KDJ指标进行股票粗筛
        :param stocks_data_dict: {symbol: dataframe}
        :param kdj_threshold: KDJ阈值
        :return: 通过筛选的股票代码列表
        """
        if kdj_threshold is None:
            kdj_threshold = self.params['kdj_threshold']
            
        filtered_symbols = []
        
        for symbol, df in stocks_data_dict.items():
            if df['J'].iloc[-1] < kdj_threshold:
                filtered_symbols.append(symbol)
        
        return filtered_symbols
        
    def get_filtered_stocks_by_date(self, stocks_data_dict, target_date, return_details=False):
        """
        获取特定日期通过B1策略筛选的所有股票
        :param stocks_data_dict: {symbol: dataframe}
        :param target_date: 'YYYY-MM-DD' 或 datetime
        :param return_details: 是否返回详细信息
        :return: 通过筛选的股票列表，或详细信息字典
        """
        if isinstance(target_date, datetime):
            target_date = target_date.strftime('%Y-%m-%d')
            
        filtered_stocks = []
        detailed_results = {}
        
        for symbol, df in stocks_data_dict.items():
            if target_date not in df.index.astype(str):
                continue
            
            date_idx = df.index.get_loc(target_date)
            if date_idx < 2:
                continue
            
            signal_triggered = False
            if self.combination_logic == "AND":
                signal_triggered = self._combine_conditions_and(df, date_idx)
            elif self.combination_logic == "OR":
                signal_triggered = self._combine_conditions_or(df, date_idx)
            elif self.combination_logic == "WEIGHTED":
                score = self._combine_conditions_weighted(df, date_idx)
                signal_triggered = score > 0.7
                
            if signal_triggered:
                if return_details:
                    detailed_results[symbol] = {
                        'date': target_date,
                        'price': df['close'].iloc[date_idx],
                        'stop_loss': df['low'].iloc[date_idx-1] * (1 - self.params['stop_loss_pct']),
                        'target_price': df['close'].iloc[date_idx] * (1 + self.params['take_profit_pct']),
                        'conditions_met': self._get_met_conditions(df, date_idx)
                    }
                else:
                    filtered_stocks.append(symbol)
                    
        if return_details:
            return detailed_results
        else:
            return filtered_stocks
            
    def _get_met_conditions(self, df, i):
        """
        获取在特定索引位置满足的条件列表
        :param df: 股票数据DataFrame
        :param i: 索引位置
        :return: 满足的条件名称列表
        """
        met_conditions = []
        for condition_name, is_active in self.active_conditions.items():
            if is_active and self.condition_functions[condition_name](df, i):
                met_conditions.append(condition_name)
        return met_conditions
