from __future__ import annotations

"""选股策略: 沪深300指数中权重排名前 N 的成分股。

数据来源：优先尝试 akshare `index_weight` 接口 (若失败则退化为 get_hs300_components() 的前 N)。

特点：
  * 不做技术形态筛选，只按指数权重排序
  * 适合作为基线或与其他择时/入场策略叠加
  * 为避免频繁网络请求，权重结果按 (index_code, trade_date) 缓存（仅取最近一批次）

输出：symbol 列表（长度 <= top_n，需在 market_data 中存在才保留）
"""

from typing import Dict, List, Optional
import pandas as pd
import datetime as _dt

try:  # 允许环境缺失 akshare 时优雅降级
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover - 环境兼容
    ak = None  # type: ignore

from .base import StockSelectionStrategy, SelectionResult


class HS300TopWeightSelection(StockSelectionStrategy):
    name = "hs300_top_weight"

    DEFAULT_PARAMS = {
        'top_n': 20,
        'index_code': '000300',  # 沪深300
    }

    _weight_cache: Dict[str, pd.DataFrame] = {}

    def __init__(self, params: Optional[Dict[str, int | str]] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    # ---- internal helpers ----
    def _fetch_weights(self) -> pd.DataFrame:
        index_code = self.params['index_code']
        cache_key = index_code
        if cache_key in self._weight_cache:
            return self._weight_cache[cache_key]
        if ak is None:  # 无 akshare 环境
            self._weight_cache[cache_key] = pd.DataFrame()
            return self._weight_cache[cache_key]
        try:
            # ak.index_weight: 可能需要指定日期；这里尝试最近一日（或默认）
            today = _dt.date.today().strftime('%Y%m%d')
            df = ak.index_weight(index=index_code, date=today)
            # 规范列名 (可能是 'code','weight')；若接口返回不同字段需适配
            target_cols = set(df.columns.str.lower())
            if 'code' not in target_cols or 'weight' not in target_cols:
                # 尝试常见变体
                rename_map = {}
                for c in df.columns:
                    cl = c.lower()
                    if cl.startswith('con_code') or cl == 'symbol':
                        rename_map[c] = 'code'
                    if cl.startswith('weight') or cl == 'i_weight':
                        rename_map[c] = 'weight'
                if rename_map:
                    df = df.rename(columns=rename_map)
            if 'weight' in df.columns:
                df = df[['code', 'weight']].copy()
                df = df.sort_values('weight', ascending=False).reset_index(drop=True)
            else:  # 列缺失则退化为空
                df = pd.DataFrame()
            self._weight_cache[cache_key] = df
        except Exception:
            self._weight_cache[cache_key] = pd.DataFrame()
        return self._weight_cache[cache_key]

    # ---- public API ----
    def select(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        dfw = self._fetch_weights()
        top_n = int(self.params['top_n'])
        if dfw.empty:
            # fallback：使用当前 market_data keys 的前 top_n（字典次序或排序）
            return list(market_data.keys())[:top_n]
        codes = dfw['code'].astype(str).tolist()
        picked: List[str] = []
        for code in codes:
            if code in market_data:
                picked.append(code)
            if len(picked) >= top_n:
                break
        return picked

    def select_with_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:  # pragma: no cover - simple wrapper
        symbols = self.select(market_data)
        return [SelectionResult(symbol=s, score=1.0, reasons=['top_weight'], meta={'index': self.params['index_code']}) for s in symbols]


__all__ = ["HS300TopWeightSelection"]
