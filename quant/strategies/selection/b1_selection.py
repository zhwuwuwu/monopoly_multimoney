from __future__ import annotations

from typing import Dict, List, Callable
import pandas as pd

from .base import StockSelectionStrategy, SelectionResult
from util.conditions import (
    is_kdj_low,
    is_bottom_pattern,
    is_big_positive,
    is_above_ma,
    is_volume_surge,
    is_volume_shrink,
    is_macd_golden_cross,
)


class B1Selection(StockSelectionStrategy):
    """B1 选股：独立实现（移除对旧 B1Strategy 依赖）。

    逻辑：在最后一根 K 线处检查一组启用的条件（默认 AND）。
    仅负责“是否纳入候选”，不生成买点细节（交给 Entry）。
    """

    name = "b1_selection"

    DEFAULT_PARAMS = {
        'kdj_threshold': 10,
        'j_threshold': -10,
        'min_trade_days': 20,
        'ma_window': 20,
        'volume_ratio': 2.0,
        'big_positive_pct': 0.05,
    }

    def __init__(self, params: Dict[str, float] | None = None, active_conditions: Dict[str, bool] | None = None, logic: str = "AND"):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.logic = logic
        self.condition_funcs: Dict[str, Callable[[pd.DataFrame, int], bool]] = {
            "kdj_condition": self._check_kdj_condition,
            "bottom_pattern_condition": self._check_bottom_pattern,
            "big_positive_condition": self._check_big_positive,
            "above_ma_condition": self._check_above_ma,
            "volume_surge_condition": self._check_volume_surge,
            "volume_shrink_condition": self._check_volume_shrink,
            "macd_golden_cross": self._check_macd_golden_cross,
        }
        self.active_conditions = active_conditions or {
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            # 其他默认关闭，可由外部注入
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False,
        }

    # ---- condition implementations (mirrored from legacy) ----
    def _check_kdj_condition(self, df: pd.DataFrame, i: int) -> bool:
        return is_kdj_low(df, i, self.params['j_threshold'])

    def _check_bottom_pattern(self, df: pd.DataFrame, i: int) -> bool:
        return is_bottom_pattern(df, i)

    def _check_big_positive(self, df: pd.DataFrame, i: int) -> bool:
        return is_big_positive(df, i, self.params['big_positive_pct'])

    def _check_above_ma(self, df: pd.DataFrame, i: int) -> bool:
        return is_above_ma(df, i, self.params['ma_window'])

    def _check_volume_surge(self, df: pd.DataFrame, i: int) -> bool:
        return is_volume_surge(df, i, self.params['volume_ratio'])

    def _check_volume_shrink(self, df: pd.DataFrame, i: int) -> bool:
        return is_volume_shrink(df, i, self.params['volume_ratio'])

    def _check_macd_golden_cross(self, df: pd.DataFrame, i: int) -> bool:
        return is_macd_golden_cross(df, i)

    # ---- condition combination ----
    def _combine(self, df: pd.DataFrame, i: int) -> bool:
        enabled = [name for name, on in self.active_conditions.items() if on]
        if not enabled:
            return False
        results = [self.condition_funcs[name](df, i) for name in enabled]
        if self.logic == 'AND':
            return all(results)
        if self.logic == 'OR':
            return any(results)
        # fallback
        return all(results)

    # ---- public ----
    def select(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:  # 向后兼容，仅返回代码
        return [r.symbol for r in self.select_with_details(market_data)]

    def select_with_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:
        detailed: List[SelectionResult] = []
        enabled = [name for name, on in self.active_conditions.items() if on]
        for symbol, df in market_data.items():
            if df is None or df.empty or len(df) < self.params['min_trade_days']:
                continue
            i = len(df) - 1
            if not enabled:
                continue
            cond_results: Dict[str, bool] = {c: self.condition_funcs[c](df, i) for c in enabled}
            passed = all(cond_results.values()) if self.logic == 'AND' else any(cond_results.values())
            if not passed:
                continue
            reasons = [c for c, ok in cond_results.items() if ok]
            # 简单“得分”：命中条件数 / 总启用条件数
            score = len(reasons) / len(enabled) if enabled else None
            detailed.append(SelectionResult(symbol=symbol, score=score, reasons=reasons, meta={'logic': self.logic}))
        return detailed

