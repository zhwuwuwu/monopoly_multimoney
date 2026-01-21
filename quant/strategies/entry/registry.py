from __future__ import annotations

"""Registry for entry strategies."""

from typing import Dict, Type
from .b1_entry import B1Entry
from .tplus1_entry import B1EntryTPlus1

ENTRY_STRATEGIES: Dict[str, Type] = {
    'b1': B1Entry,
    'b1_tplus1': B1EntryTPlus1,   # 语义上等价于 b1 + T+1 开盘执行
}


def get_entry(name: str, params=None):  # pragma: no cover
    key = name.lower()
    if key not in ENTRY_STRATEGIES:
        raise ValueError(f"未知入场策略: {name}")
    cls = ENTRY_STRATEGIES[key]
    return cls(params=params)
