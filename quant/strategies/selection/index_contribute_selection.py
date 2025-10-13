from __future__ import annotations

"""index_contribute_selection

通用“成分/板块/指数权重 TopK” 选股策略。

支持来源 (mode):
  - index    : 指数代码（如 000300, 000905 等），使用 ak.index_weight 获取权重
  - concept  : 概念板块代码（ak.stock_board_concept_cons_em），无官方权重 → 以最新总市值/流通市值估算排序
  - industry : 行业板块代码（ak.stock_board_industry_cons_em），同上用市值排序
  - etf      : 预留（暂未实现 constituents 抓取，抛出 NotImplementedError）

权重估算策略：
  1. 对 index 模式直接用接口返回 weight 字段
  2. 对 concept / industry 获取成分后尝试调用 ak.stock_zh_a_spot_em 获取全市场快照，
     用 '总市值' 或 '流通市值' 作为排序依据 (降序)，作为 proxy weight。
  3. 任一数据获取失败时退化为使用原列表顺序截取 top_n。

输出：symbol list；`select_with_details` 返回每只股票的 proxy_weight (若可得)。

参数：
  mode: str  (index|concept|industry|etf)
  code: str  (指数或板块代码)
  top_n: int (默认20)
  date: str  (YYYYMMDD，可选；指数权重接口需要。缺省用今日)
  use_float_mv: bool (使用流通市值而非总市值排序；仅 concept/industry 模式下)

注意：本策略只做“成分权重排名”层面的横截面过滤，不包含任何技术形态/因子条件。
"""

from typing import Dict, List, Optional
import datetime as _dt
import pandas as pd

try:  # 允许无 akshare 环境
    import akshare as ak  # type: ignore
except Exception:  # pragma: no cover
    ak = None  # type: ignore

from .base import StockSelectionStrategy, SelectionResult


class IndexContributeSelection(StockSelectionStrategy):
    name = "index_contribute_selection"

    DEFAULT_PARAMS = {
        'mode': 'index',        # index | concept | industry | etf
        'code': '000300',       # 指数或板块代码
        'top_n': 20,
        'date': None,           # 指定权重日期 (YYYYMMDD)；None=今日
        'use_float_mv': True,   # concept/industry 使用流通市值排序
    }

    def __init__(self, params: Optional[Dict[str, object]] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}

    # ---- helpers ----
    def _today_str(self) -> str:
        return _dt.date.today().strftime('%Y%m%d')

    def _fetch_index_weights(self, code: str, date: Optional[str]) -> pd.DataFrame:
        if ak is None:
            return pd.DataFrame()
        d = date or self._today_str()
        try:
            df = ak.index_weight(index=code, date=d)
            # 规范列
            lower = {c.lower(): c for c in df.columns}
            code_col = lower.get('code') or lower.get('con_code') or lower.get('symbol')
            weight_col = lower.get('weight') or lower.get('i_weight')
            if code_col and weight_col:
                out = df[[code_col, weight_col]].copy()
                out.columns = ['code', 'weight']
                out = out.sort_values('weight', ascending=False).reset_index(drop=True)
                return out
        except Exception:
            pass
        return pd.DataFrame()

    def _fetch_board_members(self, code: str, mode: str) -> pd.DataFrame:
        if ak is None:
            return pd.DataFrame()
        try:
            if mode == 'concept':
                df = ak.stock_board_concept_cons_em(symbol=code)
            elif mode == 'industry':
                df = ak.stock_board_industry_cons_em(symbol=code)
            else:
                return pd.DataFrame()
            # 统一股票代码列
            for cand in ['代码', '股票代码', 'code']:
                if cand in df.columns:
                    df = df.rename(columns={cand: 'code'})
                    break
            if 'code' not in df.columns:
                return pd.DataFrame()
            return df
        except Exception:
            return pd.DataFrame()

    def _fetch_market_snapshot(self) -> pd.DataFrame:
        if ak is None:
            return pd.DataFrame()
        try:
            snap = ak.stock_zh_a_spot_em()
            # 统一代码列
            for cand in ['代码', '股票代码', 'code']:
                if cand in snap.columns:
                    snap = snap.rename(columns={cand: 'code'})
                    break
            return snap
        except Exception:
            return pd.DataFrame()

    def _board_with_weights(self, code: str, mode: str) -> pd.DataFrame:
        members = self._fetch_board_members(code, mode)
        if members.empty:
            return members
        snap = self._fetch_market_snapshot()
        if snap.empty:
            return members.assign(weight=None)
        # 选市值列
        float_mv_cols = [c for c in snap.columns if '流通市值' in c]
        total_mv_cols = [c for c in snap.columns if '总市值' in c]
        mv_col = None
        if self.params.get('use_float_mv') and float_mv_cols:
            mv_col = float_mv_cols[0]
        elif total_mv_cols:
            mv_col = total_mv_cols[0]
        if mv_col is None:
            return members.assign(weight=None)
        merged = members.merge(snap[['code', mv_col]], on='code', how='left')
        merged = merged.rename(columns={mv_col: 'weight'})
        merged = merged.sort_values('weight', ascending=False, na_position='last')
        return merged

    # ---- public ----
    def select(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        mode = str(self.params['mode']).lower()
        code = str(self.params['code'])
        top_n = int(self.params['top_n'])

        if mode == 'etf':  # 预留：后续可接入 ETF 成分获取
            raise NotImplementedError("ETF 成分权重获取暂未实现")

        if mode == 'index':
            dfw = self._fetch_index_weights(code, self.params.get('date'))
        elif mode in ('concept', 'industry'):
            dfw = self._board_with_weights(code, mode)
        else:
            raise ValueError(f"未知 mode: {mode}")

        if dfw.empty:
            return []
        # 统一列名 code / weight (board 可能权重为空)
        if 'code' not in dfw.columns:
            return []
        symbols = []
        for sym in dfw['code'].astype(str):
            if sym in market_data:  # 只返回当前传入市场数据里有的
                symbols.append(sym)
            if len(symbols) >= top_n:
                break
        return symbols

    def select_with_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:  # pragma: no cover
        mode = str(self.params['mode']).lower()
        code = str(self.params['code'])
        top_n = int(self.params['top_n'])
        try:
            if mode == 'index':
                dfw = self._fetch_index_weights(code, self.params.get('date'))
            else:
                dfw = self._board_with_weights(code, mode)
        except Exception:
            dfw = pd.DataFrame()
        if dfw.empty or 'code' not in dfw.columns:
            return []
        rows = []
        taken = 0
        for _, row in dfw.iterrows():
            sym = str(row['code'])
            if sym not in market_data:
                continue
            weight_val = row.get('weight') if 'weight' in row else None
            rows.append(SelectionResult(symbol=sym, score=None, reasons=['top_weight'], meta={'mode': mode, 'source_code': code, 'weight': weight_val}))
            taken += 1
            if taken >= top_n:
                break
        return rows

__all__ = ["IndexContributeSelection"]
