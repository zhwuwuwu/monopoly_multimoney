from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd

from .base import EntrySignalStrategy
from util.conditions import (
    is_kdj_low,
    is_bottom_pattern,
    is_big_positive,
    is_above_ma,
)


class B1Entry(EntrySignalStrategy):
    """独立 B1 入场信号：与选股条件相同，但只返回“最后一根触发”的即时买点。

    stop_loss = 前一根 low * (1 - stop_loss_pct)
    target = 当日 close * (1 + take_profit_pct)
    """

    name = "b1_entry"

    DEFAULT_PARAMS = {
        'stop_loss_pct': 0.12,
        'take_profit_pct': 0.3,
        'min_trade_days': 20,
        'j_threshold': -10,
        'big_positive_pct': 0.05,
        'ma_window': 20,
    }

    def __init__(self, params: Dict[str, float] | None = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    # 复用与选股一致的几个条件：J 低位 + 底分型 + 大阳线 + 均线之上
    def _check_kdj(self, df: pd.DataFrame, i: int) -> bool:
        return is_kdj_low(df, i, self.params['j_threshold'])

    def _check_bottom(self, df: pd.DataFrame, i: int) -> bool:
        return is_bottom_pattern(df, i)

    def _check_big_positive(self, df: pd.DataFrame, i: int) -> bool:
        return is_big_positive(df, i, self.params['big_positive_pct'])

    def _check_above_ma(self, df: pd.DataFrame, i: int) -> bool:
        return is_above_ma(df, i, self.params['ma_window'])

    def _trigger(self, df: pd.DataFrame, i: int) -> bool:
        return all([
            self._check_kdj(df, i),
            self._check_bottom(df, i),
            self._check_big_positive(df, i),
            self._check_above_ma(df, i),
        ])

    def generate(self, symbol: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or df.empty or len(df) < self.params['min_trade_days']:
            return []
        i = len(df) - 1
        if not self._trigger(df, i):
            return []
        price = float(df['close'].iloc[i])
        stop_loss = float(df['low'].iloc[i-1] * (1 - self.params['stop_loss_pct'])) if i >= 1 else price * 0.88
        target = price * (1 + self.params['take_profit_pct'])
        return [{
            "symbol": symbol,
            "date": df.index[i],
            "price": price,
            "stop_loss": stop_loss,
            "target_price": target,
            "meta": {"source": "b1_entry_independent"},
        }]

