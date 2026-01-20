from __future__ import annotations

"""Advanced / alternative exit strategies.

Contains several common patterns:
  - TimeBasedExit: exit after holding N days.
  - TrailingStopExit: dynamic trailing stop based on highest price (long side).
  - AdvancedExit: combines fixed stop_loss/target + trailing + time + optional
    reward-to-risk locking.

All strategies implement ExitSignalStrategy and only read / (optionally) mutate
the position dict (e.g. updating highest_price). They return ExitDecision.

NOTE: Positions are assumed to be long only for trailing logic; extension to
short can be added by mirroring conditions.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

from .base import ExitSignalStrategy, ExitDecision


@dataclass
class TimeBasedExit(ExitSignalStrategy):
    name: str = "time_exit"
    max_holding_days: int = 10

    def evaluate(self, position: Dict[str, Any], bar: Dict[str, Any]) -> ExitDecision:  # type: ignore[override]
        holding_days = (bar['date'] - position['entry_date']).days
        if holding_days >= self.max_holding_days:
            return ExitDecision(True, "time_stop", bar['close'])
        return ExitDecision(False)


@dataclass
class TrailingStopExit(ExitSignalStrategy):
    name: str = "trailing_exit"
    trailing_pct: float = 0.1  # 10% retrace from peak triggers exit

    def evaluate(self, position: Dict[str, Any], bar: Dict[str, Any]) -> ExitDecision:  # type: ignore[override]
        price = float(bar['close'])
        # Initialize / update highest_price
        hp = position.get('highest_price')
        if hp is None or price > hp:
            position['highest_price'] = price
            return ExitDecision(False)  # no exit while making new highs
        hp = position['highest_price']
        if price <= hp * (1 - self.trailing_pct):
            return ExitDecision(True, "trailing_stop", price)
        return ExitDecision(False)


@dataclass
class AdvancedExit(ExitSignalStrategy):
    """Composite exit: fixed stop / target + trailing + time.

    Priority order (first match exits):
      1. stop_loss (capital preservation)
      2. trailing stop (protect gains)
      3. take profit (static target)
      4. time stop (stale position)
    """

    name: str = "advanced_exit"
    trailing_pct: Optional[float] = 0.12
    max_holding_days: Optional[int] = 40
    lock_profit_after_rr: Optional[float] = None  # e.g. 2.0 → move stop to break-even

    def evaluate(self, position: Dict[str, Any], bar: Dict[str, Any]) -> ExitDecision:  # type: ignore[override]
        price = float(bar['close'])
        entry_px = float(position['entry_price'])

        # 1) stop loss
        sl = position.get('stop_loss')
        if sl is not None and price <= sl:
            return ExitDecision(True, 'stop_loss', price)

        # Update / init highest price
        hp = position.get('highest_price')
        if hp is None or price > hp:
            position['highest_price'] = price
            hp = price

        # Optional dynamic lock: if reward >= lock_profit_after_rr * initial risk, move SL to entry
        if self.lock_profit_after_rr is not None and sl is not None:
            risk = entry_px - sl
            if risk > 0 and (price - entry_px) >= risk * self.lock_profit_after_rr:
                # elevate stop to break-even (entry price) if not already higher
                if position['stop_loss'] < entry_px:
                    position['stop_loss'] = entry_px

        # 2) trailing stop
        if self.trailing_pct is not None and hp is not None:
            if price <= hp * (1 - self.trailing_pct):
                return ExitDecision(True, 'trailing_stop', price)

        # 3) take profit
        tp = position.get('target_price')
        if tp is not None and price >= tp:
            return ExitDecision(True, 'take_profit', price)

        # 4) time based
        if self.max_holding_days is not None:
            holding_days = (bar['date'] - position['entry_date']).days
            if holding_days >= self.max_holding_days:
                return ExitDecision(True, 'time_stop', price)

        return ExitDecision(False)


__all__ = [
    'TimeBasedExit',
    'TrailingStopExit',
    'AdvancedExit',
]
