from __future__ import annotations

from typing import Dict, Any, List


class Portfolio:
    def __init__(self, capital: float):
        self.cash = float(capital)
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.history: List[Dict[str, Any]] = []

    def add_position(self, symbol: str, shares: int, price: float, meta: Dict[str, Any]):
        self.positions[symbol] = {"symbol": symbol, "shares": shares, "entry_price": price, **meta}

    def remove_position(self, symbol: str):
        self.positions.pop(symbol, None)

    def mark_to_market(self, date, prices: Dict[str, float]):
        total_value = self.cash
        for sym, pos in self.positions.items():
            px = prices.get(sym)
            if px is not None:
                total_value += px * pos["shares"]
        self.history.append({"date": date, "total_value": total_value, "cash": self.cash, "positions": len(self.positions)})
        return total_value
