from __future__ import annotations
from typing import Dict, Callable
from .simple_models import CloseExecutionModel, NextOpenExecutionModel, VWAPApproxExecutionModel

EXECUTION_MODELS: Dict[str, Callable[[], object]] = {
    'close': CloseExecutionModel,
    'next_open': NextOpenExecutionModel,
    'tplus1': NextOpenExecutionModel,  # alias
    't+1': NextOpenExecutionModel,     # alias
    'vwap': VWAPApproxExecutionModel,
}

def get_execution_model(name: str):
    key = name.lower()
    if key not in EXECUTION_MODELS:
        raise ValueError(f"未知执行模型: {name}")
    return EXECUTION_MODELS[key]()

__all__ = ["get_execution_model"]
