from __future__ import annotations

from typing import Dict, Any

from .base import ExitSignalStrategy, ExitDecision


class FixedRiskExit(ExitSignalStrategy):
    name = "fixed_risk"

    def evaluate(self, position: Dict[str, Any], bar: Dict[str, Any]) -> ExitDecision:
        price = float(bar["close"])
        if position.get("stop_loss") is not None and price <= position["stop_loss"]:
            return ExitDecision(True, "stop_loss", price)
        if position.get("target_price") is not None and price >= position["target_price"]:
            return ExitDecision(True, "take_profit", price)
        return ExitDecision(False)
