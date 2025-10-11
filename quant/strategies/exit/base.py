from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ExitDecision:
    exit: bool
    reason: str = ""
    price: float | None = None


class ExitSignalStrategy(ABC):
    """出场信号策略基类。

    evaluate 传入当前持仓 & 新的行情 bar，返回 ExitDecision。
    """

    name: str = "base_exit"

    @abstractmethod
    def evaluate(self, position: Dict[str, Any], bar: Dict[str, Any]) -> ExitDecision:  # pragma: no cover
        raise NotImplementedError
