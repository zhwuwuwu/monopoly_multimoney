from __future__ import annotations

from typing import Dict, Any, List
from .models import DaySnapshot


class Portfolio:
    def __init__(self, capital: float):
        self.cash = float(capital)
        self.positions: Dict[str, Dict[str, Any]] = {}
        # history keeps list of DaySnapshot (as dict for backwards compatibility)
        self.history = []  # type: List[Dict[str, Any]]

    def add_position(self, symbol: str, shares: int, price: float, meta: Dict[str, Any]):
        self.positions[symbol] = {"symbol": symbol, "shares": shares, "entry_price": price, **meta}

    def remove_position(self, symbol: str):
        self.positions.pop(symbol, None)

    def mark_to_market(self, date, prices: Dict[str, float]):
        """Backward compatible close-session mark to market.

        Deprecated: prefer ``mark_session``.
        """
        return self.mark_session(date, 'close', prices)

    def mark_session(self, date, session: str, prices: Dict[str, float]):
        """Record a portfolio snapshot for a given session ('open'/'close').

        The valuation uses the provided mapping of symbol->price; caller decides
        whether to pass open or close prices.
        """
        total_value = self.cash
        for sym, pos in self.positions.items():
            px = prices.get(sym)
            if px is not None:
                total_value += px * pos['shares']
        snap = DaySnapshot(date=date, session=session, total_value=total_value,
                           cash=self.cash, positions=len(self.positions))
        self.history.append(snap.as_dict())
        return total_value
