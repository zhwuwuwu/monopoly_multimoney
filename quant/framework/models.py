from __future__ import annotations

"""Core datamodel objects used by the backtesting framework.

This module introduces lightweight dataclasses to standardise the in‑memory
representation of trades, positions and daily portfolio snapshots while
keeping backwards compatibility (existing code that consumes simple dicts
will continue to work because we keep exporting ``as_dict()`` helpers).

Design principles:
  * Immutable public snapshot objects (``Trade``, ``DaySnapshot``) – created
    once and never mutated. (Internal portfolio still mutates a mutable
    position dict for performance / simplicity.)
  * Serialization friendly: ``as_dict()`` returns only primitive / JSON
    serialisable types (datetime left as pandas.Timestamp which is also fine
    for most downstream tooling; convert externally if needed).
  * Optional fields kept minimal to avoid wide sparse structures.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
import pandas as pd


@dataclass(slots=True)
class Trade:
    date: pd.Timestamp
    symbol: str
    action: str              # BUY / SELL
    price: float
    shares: int
    commission: float
    pnl: float               # realised PnL for SELL, 0 for BUY
    reason: str = ""
    session: str = "close"   # 'open' or 'close'
    signal_date: Optional[pd.Timestamp] = None

    def as_dict(self) -> Dict[str, Any]:  # pragma: no cover - trivial
        return {
            'date': self.date,
            'symbol': self.symbol,
            'action': self.action,
            'price': self.price,
            'shares': self.shares,
            'commission': self.commission,
            'pnl': self.pnl,
            'reason': self.reason,
            'session': self.session,
            'signal_date': self.signal_date,
        }


@dataclass(slots=True)
class DaySnapshot:
    date: pd.Timestamp
    session: str             # 'open' or 'close'
    total_value: float
    cash: float
    positions: int
    # optional per‑session analytics – can be extended later

    def as_dict(self) -> Dict[str, Any]:  # pragma: no cover - trivial
        return {
            'date': self.date,
            'session': self.session,
            'total_value': self.total_value,
            'cash': self.cash,
            'positions': self.positions,
        }


__all__ = [
    'Trade',
    'DaySnapshot',
]
