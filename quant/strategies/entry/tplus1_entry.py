from __future__ import annotations

"""T+1 开盘买入版本的 B1 入场策略。

思路：复用 B1Entry 的触发逻辑，但不在信号当日收盘买入，
而是生成一个包含 exec_date (下一交易日) 与 exec_price_type = 'open' 的延迟执行信号。

Backtester 需要识别信号中的 exec_date / exec_price_type，
在对应日期到来时按开盘价撮合（见 backtester 中的 pending_entries 处理）。
"""

from typing import Dict, Any, List
import pandas as pd

from .b1_entry import B1Entry


class B1EntryTPlus1(B1Entry):
    name = "b1_entry_tplus1"

    def generate(self, symbol: str, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # 复用父类生成逻辑（得到当日触发信号，价格等 still 基于信号日 close）
        base_signals = super().generate(symbol, df)
        if not base_signals:
            return []
        i = len(df) - 1
        # 下一交易日（若数据不足则放弃该信号，避免未来数据泄露）
        if i + 1 >= len(df.index):
            return []
        next_dt = df.index[i + 1]
        enriched = []
        for sig in base_signals:
            sig = {**sig}  # copy
            sig['exec_date'] = next_dt
            sig['exec_price_type'] = 'open'  # 在下一根的开盘成交
            sig['meta'] = {**sig.get('meta', {}), 'execution': 'T+1_open'}
            enriched.append(sig)
        return enriched
