from __future__ import annotations

"""Registry for selection strategies."""

from typing import Dict, Type
from .b1_selection import B1Selection

SELECTION_STRATEGIES: Dict[str, Type] = {
    'b1': B1Selection,
}


def get_selection(name: str, params=None):  # pragma: no cover (simple factory)
    key = name.lower()
    if key not in SELECTION_STRATEGIES:
        raise ValueError(f"未知选股策略: {name}")
    cls = SELECTION_STRATEGIES[key]
    return cls(params=params)
