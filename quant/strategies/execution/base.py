from __future__ import annotations
"""Execution model base abstractions.
See simple_models for concrete implementations.
"""
from typing import List, Dict, Any, Sequence, Protocol
import pandas as pd

class ExecutionModel(Protocol):  # structural typing
    def plan(self, signals: List[Dict[str, Any]], current_date: pd.Timestamp, calendar: Sequence[pd.Timestamp]) -> List[Dict[str, Any]]:
        """Transform raw entry signals (no exec_date) into planned orders.
        Must add: exec_date, exec_price_type, signal_date.
        """
        ...  # pragma: no cover

    def resolve_price(self, df, exec_date: pd.Timestamp, price_type: str) -> float:
        """Return execution price for symbol dataframe at exec_date."""
        ...  # pragma: no cover

__all__ = ["ExecutionModel"]
