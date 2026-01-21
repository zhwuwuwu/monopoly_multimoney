from __future__ import annotations

from typing import Dict, Any, List, Optional
import dataclasses
import pandas as pd
from strategies.selection.base import SelectionResult


def _extract_params(obj) -> Optional[Dict[str, Any]]:
    """Best-effort 获取策略参数快照：
    1) 若存在 .params 属性且为 dict
    2) 若是 dataclass 则 asdict
    3) 否则返回 None
    """
    if hasattr(obj, 'params') and isinstance(getattr(obj, 'params'), dict):
        return dict(getattr(obj, 'params'))
    if dataclasses.is_dataclass(obj):
        try:
            return dataclasses.asdict(obj)  # type: ignore[arg-type]
        except Exception:  # pragma: no cover - 保护性
            return None
    return None


class CompositeStrategy:
    """四层策略组合基类（selection - entry - exit - execution）。

    该组合只做"编排 (orchestration)"：
      1. 调用选股策略 selection.select -> 得到候选标的列表
      2. 对每个标的调用入场策略 entry.generate -> 收集入场信号
      3. 通过执行模型 execution_model 转换信号为订单
      4. 回测循环里由外部调用 evaluate_exit -> 调用 exit_rule.evaluate

    设计目标：
      - 解耦：四个策略互不依赖，便于替换 / 复用 / 组合
      - 可追踪：记录各层策略名称与参数快照，提升复现性
      - 完整性：强制包含选股-入场-退出-执行四层

    参数:
      selection: 选股策略实例
      entry: 入场策略实例
      exit_rule: 退出策略实例
      execution_model: 执行模式实例
      name: 组合名称
    """

    def __init__(self, selection, entry, exit_rule, execution_model, name: str):
        self.selection = selection
        self.entry = entry
        self.exit_rule = exit_rule
        self.execution_model = execution_model
        self.name = name

        # 记录组件名称
        self.selection_name = getattr(selection, 'name', selection.__class__.__name__)
        self.entry_name = getattr(entry, 'name', entry.__class__.__name__)
        self.exit_name = getattr(exit_rule, 'name', exit_rule.__class__.__name__)
        self.execution_name = getattr(execution_model, 'name', execution_model.__class__.__name__)

        # 参数快照
        self.config: Dict[str, Any] = {
            'selection': {
                'name': self.selection_name,
                'params': _extract_params(selection)
            },
            'entry': {
                'name': self.entry_name,
                'params': _extract_params(entry)
            },
            'exit': {
                'name': self.exit_name,
                'params': _extract_params(exit_rule)
            },
            'execution': {
                'name': self.execution_name,
                'params': _extract_params(execution_model)
            },
            'composite_name': self.name,
        }

    # ---------- Orchestration ----------
    def select_universe(self, market_data: Dict[str, pd.DataFrame]) -> List[str]:
        return self.selection.select(market_data)

    def generate_entries(self, market_data: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        for sym in self.select_universe(market_data):
            df = market_data.get(sym)
            if df is None:
                continue
            sym_signals = self.entry.generate(sym, df) or []
            # 给信号附加层信息
            for sig in sym_signals:
                sig.setdefault('meta', {})
                sig['meta'].setdefault('selection', self.selection_name)
                sig['meta'].setdefault('entry', self.entry_name)
                sig['meta'].setdefault('execution', self.execution_name)
            signals.extend(sym_signals)
        return signals

    def evaluate_exit(self, position: Dict[str, Any], bar: Dict[str, Any]):
        return self.exit_rule.evaluate(position, bar)

    # ---------- Introspection / Helpers ----------
    def to_dict(self) -> Dict[str, Any]:
        return dict(self.config)

    def summary(self) -> str:
        return (f"CompositeStrategy(name={self.name}, selection={self.selection_name}, "
                f"entry={self.entry_name}, exit={self.exit_name}, execution={self.execution_name})")

    def __repr__(self) -> str:
        return self.summary()

    def selection_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:
        sel = getattr(self.selection, 'select_with_details', None)
        if callable(sel):
            return sel(market_data)
        symbols = self.selection.select(market_data)
        return [SelectionResult(symbol=s) for s in symbols]


__all__ = ['CompositeStrategy']
