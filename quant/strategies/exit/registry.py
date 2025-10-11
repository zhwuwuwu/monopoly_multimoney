from __future__ import annotations

"""Registry for exit strategies."""

from typing import Dict, Type
from .fixed_risk_exit import FixedRiskExit
from .advanced_exit import TimeBasedExit, TrailingStopExit, AdvancedExit

EXIT_STRATEGIES: Dict[str, Type] = {
    'fixed': FixedRiskExit,
    'time': TimeBasedExit,
    'trailing': TrailingStopExit,
    'advanced': AdvancedExit,
}


def get_exit(name: str, params=None):  # pragma: no cover
    key = name.lower()
    if key not in EXIT_STRATEGIES:
        raise ValueError(f"未知退出策略: {name}")
    cls = EXIT_STRATEGIES[key]
    params = params or {}
    return cls(**params)
