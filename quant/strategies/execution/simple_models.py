from __future__ import annotations
from typing import List, Dict, Any, Sequence
import pandas as pd
from .base import ExecutionModel

class CloseExecutionModel:
    name = "close"
    def plan(self, signals: List[Dict[str, Any]], current_date: pd.Timestamp, calendar: Sequence[pd.Timestamp]) -> List[Dict[str, Any]]:  # type: ignore[override]
        planned: List[Dict[str, Any]] = []
        for sig in signals:
            if 'exec_date' in sig:
                planned.append(sig)
                continue
            new_sig = {**sig}
            new_sig.setdefault('meta', {})
            new_sig['exec_date'] = current_date
            new_sig['exec_price_type'] = 'close'
            new_sig['signal_date'] = sig.get('date', current_date)
            new_sig['meta'].setdefault('execution_model', self.name)
            planned.append(new_sig)
        return planned
    def resolve_price(self, df, exec_date: pd.Timestamp, price_type: str) -> float:  # type: ignore[override]
        return float(df.loc[exec_date, 'close'])

class NextOpenExecutionModel:
    name = "next_open"
    def plan(self, signals: List[Dict[str, Any]], current_date: pd.Timestamp, calendar: Sequence[pd.Timestamp]) -> List[Dict[str, Any]]:  # type: ignore[override]
        planned: List[Dict[str, Any]] = []
        if not calendar:
            return []
        # find next date
        try:
            idx = list(calendar).index(current_date)
            next_dt = calendar[idx + 1]
        except (ValueError, IndexError):
            return []
        for sig in signals:
            if 'exec_date' in sig:
                planned.append(sig)
                continue
            new_sig = {**sig}
            new_sig.setdefault('meta', {})
            new_sig['exec_date'] = next_dt
            new_sig['exec_price_type'] = 'open'
            new_sig['signal_date'] = sig.get('date', current_date)
            new_sig['meta'].setdefault('execution_model', self.name)
            planned.append(new_sig)
        return planned
    def resolve_price(self, df, exec_date: pd.Timestamp, price_type: str) -> float:  # type: ignore[override]
        return float(df.loc[exec_date, 'open'])

class VWAPApproxExecutionModel:
    name = "vwap_approx"
    def plan(self, signals: List[Dict[str, Any]], current_date: pd.Timestamp, calendar: Sequence[pd.Timestamp]) -> List[Dict[str, Any]]:  # type: ignore[override]
        planned: List[Dict[str, Any]] = []
        for sig in signals:
            if 'exec_date' in sig:
                planned.append(sig)
                continue
            new_sig = {**sig}
            new_sig.setdefault('meta', {})
            new_sig['exec_date'] = current_date
            new_sig['exec_price_type'] = 'vwap'
            new_sig['signal_date'] = sig.get('date', current_date)
            new_sig['meta'].setdefault('execution_model', self.name)
            planned.append(new_sig)
        return planned
    def resolve_price(self, df, exec_date: pd.Timestamp, price_type: str) -> float:  # type: ignore[override]
        row = df.loc[exec_date]
        return float((row['open'] + row['close']) / 2)

__all__ = [
    'CloseExecutionModel',
    'NextOpenExecutionModel',
    'VWAPApproxExecutionModel',
]
