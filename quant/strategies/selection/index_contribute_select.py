from __future__ import annotations

"""通用权重/成份贡献选股策略: index_contribute_select

支持从 指数 / ETF 持仓（后续可扩展概念、板块）中挑选权重排名 TopK 的成份股，
作为后续入场策略的候选集合。

参数:
  source_type: 'index' | 'etf'   （未来可扩展 'concept', 'industry'）
  code:        指数代码 (例如 000300) / ETF 代码（如 510300）
  top_k:       选取前 K 只（默认 20）
  allow_missing: 当无法获取权重数据时，是否退化为使用 market_data 中前 K 只

数据来源 (akshare):
  指数: ak.index_weight(index=code, date='YYYYMMDD')
  ETF : ak.fund_portfolio_hold_em(symbol=code)  (持仓公布为季度/定期，不一定与回测日对齐)

输出: List[str]  股票代码序列 (仅保留出现在当前 market_data 的成份)
select_with_details: 返回 SelectionResult，reasons=['weight_top'], meta={source_type, code}

注意:
  - 不做任何技术面过滤，也不计算 score（统一 1.0）。
  - 权重数据会简单缓存到类级别，减少重复请求。
  - ETF / 指数权重接口若失败 => 依据 allow_missing 决定返回空或 fallback。
"""

from typing import Dict, List, Optional
import datetime as _dt
import pandas as pd

try:  # 允许没有 akshare 环境
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover
    ak = None  # type: ignore

from .base import StockSelectionStrategy, SelectionResult


class IndexContributeSelect(StockSelectionStrategy):
    name = 'index_contribute_select'

    DEFAULT_PARAMS = {
        'source_type': 'index',   # 'index' | 'etf'
        'code': '000300',         # 指数 / ETF 代码
        'top_k': 20,
        'allow_missing': True,
    }

    _cache: Dict[str, pd.DataFrame] = {}

    def __init__(self, params: Optional[Dict[str, object]] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    # ---- internal fetch helpers ----
    def _fetch_index_weights(self, code: str) -> pd.DataFrame:
        if ak is None:
            return pd.DataFrame()
        today = _dt.date.today().strftime('%Y%m%d')
        try:
            df = ak.index_weight(index=code, date=today)
        except Exception:
            return pd.DataFrame()
        return self._normalize(df, usage='index')

    def _fetch_etf_weights(self, code: str) -> pd.DataFrame:
        if ak is None:
            return pd.DataFrame()
        try:
            df = ak.fund_portfolio_hold_em(symbol=code)
        except Exception:
            return pd.DataFrame()
        # 常见列：'股票代码','持股市值占净值比' 等
        return self._normalize(df, usage='etf')

    def _normalize(self, df: pd.DataFrame, usage: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        df2 = df.copy()
        lower_map = {c.lower(): c for c in df2.columns}
        code_col = None
        weight_col = None
        # 可能的列名集合
        code_candidates = ['code', '股票代码', 'con_code', 'symbol']
        weight_candidates = ['weight', '权重', '持股市值占净值比', 'i_weight']
        for cand in code_candidates:
            if cand in lower_map:
                code_col = lower_map[cand]
                break
            # 直接匹配原列
            for orig in df2.columns:
                if orig == cand:
                    code_col = orig
                    break
        for cand in weight_candidates:
            if cand in lower_map:
                weight_col = lower_map[cand]
                break
            for orig in df2.columns:
                if orig == cand:
                    weight_col = orig
                    break
        if not code_col:
            return pd.DataFrame()
        if not weight_col:
            # 没有权重列则给一个默认值 1 以保证返回；后续排序相同
            df2['_weight'] = 1.0
            weight_col = '_weight'
        # 规范输出
        out = pd.DataFrame({
            'code': df2[code_col].astype(str).str.zfill(6),
            'weight': pd.to_numeric(df2[weight_col], errors='coerce').fillna(0.0)
        })
        out = out.sort_values('weight', ascending=False).reset_index(drop=True)
        return out

    def _get_weights(self) -> pd.DataFrame:
        code = str(self.params['code'])
        source_type = str(self.params['source_type']).lower()
        cache_key = f"{source_type}:{code}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        if source_type == 'index':
            dfw = self._fetch_index_weights(code)
        elif source_type == 'etf':
            dfw = self._fetch_etf_weights(code)
        else:
            dfw = pd.DataFrame()
        self._cache[cache_key] = dfw
        return dfw

    # ---- public API ----
    def select(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        dfw = self._get_weights()
        top_k = int(self.params['top_k'])
        allow_missing = bool(self.params.get('allow_missing', True))
        if dfw.empty:
            return list(market_data.keys())[:top_k] if allow_missing else []
        picked: List[str] = []
        for code in dfw['code']:
            if code in market_data:
                picked.append(code)
            if len(picked) >= top_k:
                break
        if not picked and allow_missing:
            return list(market_data.keys())[:top_k]
        return picked

    def select_with_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:  # pragma: no cover
        symbols = self.select(market_data)
        meta_common = {
            'source_type': self.params['source_type'],
            'code': self.params['code'],
        }
        return [SelectionResult(symbol=s, score=1.0, reasons=['weight_top'], meta=meta_common) for s in symbols]


__all__ = ['IndexContributeSelect']
