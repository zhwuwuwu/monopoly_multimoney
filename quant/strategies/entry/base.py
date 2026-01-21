from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import pandas as pd


class EntrySignalStrategy(ABC):
    """入场信号策略基类。

    generate 返回 0..n 条入场信号（允许同一天多个逻辑）。
    每个信号建议字段：symbol,date,price,stop_loss,target_price,meta。
    """

    name: str = "base_entry"

    @abstractmethod
    def generate(self, symbol: str, df: pd.DataFrame) -> List[Dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError
