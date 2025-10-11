"""通用选股筛选执行模块。

拆分自 legacy b1_stock_filter，以复用：
1. 股票池准备
2. 数据加载
3. 执行 selection strategy
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import os
import pandas as pd

from util.market_data_handler import MarketDataHandler


@dataclass
class ScreenResult:
    symbol: str
    date: Any
    price: float
    stop_loss: float
    target_price: float
    meta: Dict[str, Any]


class StockPoolProvider:
    def __init__(self, data_handler: Optional[MarketDataHandler] = None, verbose: bool = True):
        self.data_handler = data_handler or MarketDataHandler()
        self.verbose = verbose

    def get_symbols(self, pool: str, symbols: Optional[List[str]] = None) -> List[str]:
        pool = pool.lower()
        if pool == "hs300":
            syms = self.data_handler.get_hs300_components()
        elif pool == "zz500":
            syms = self.data_handler.get_zz500_components()
        elif pool == "all_a":
            syms = self.data_handler.get_all_a_stocks()
        elif pool == "main":
            syms = self.data_handler.get_main_board_stocks()
        elif pool == "custom" and symbols is not None:
            syms = symbols
        else:
            syms = self.data_handler.get_hs300_components()
        if self.verbose:
            print(f"股票池 {pool}: {len(syms)} 只")
        return syms


class StockScreener:
    def __init__(self, data_handler: Optional[MarketDataHandler] = None, history_days: int = 45, verbose: bool = True):
        self.data_handler = data_handler or MarketDataHandler()
        self.history_days = history_days
        self.verbose = verbose

    def load_stock_data(self, symbols: List[str], target_date: str) -> Dict[str, pd.DataFrame]:
        tgt = datetime.strptime(target_date, '%Y-%m-%d')
        start = (tgt - timedelta(days=self.history_days)).strftime('%Y%m%d')
        end = tgt.strftime('%Y%m%d')
        data: Dict[str, pd.DataFrame] = {}
        for s in symbols:
            df = self.data_handler.get_stock_data(s, start, end)
            if df is not None and len(df) > 20 and target_date in df.index.astype(str):
                data[s] = df
        if self.verbose:
            print(f"加载有效股票数据: {len(data)} 条")
        return data

    def run(self, selection_strategy, symbols: List[str], target_date: str) -> List[ScreenResult]:
        market_data = self.load_stock_data(symbols, target_date)
        selected = selection_strategy.select(market_data)
        results: List[ScreenResult] = []
        for sym in selected:
            df = market_data[sym]
            last = df.iloc[-1]
            results.append(ScreenResult(
                symbol=sym,
                date=df.index[-1],
                price=float(last['close']),
                stop_loss=float(last['low'] * 0.9),  # placeholder risk model
                target_price=float(last['close'] * 1.3),
                meta={"selection": selection_strategy.name}
            ))
        return results

    @staticmethod
    def to_dict(results: List[ScreenResult]) -> Dict[str, Dict[str, Any]]:
        return {r.symbol: {
            'date': r.date,
            'price': r.price,
            'stop_loss': r.stop_loss,
            'target_price': r.target_price,
            'conditions_met': [r.meta.get('selection', '')]
        } for r in results}
