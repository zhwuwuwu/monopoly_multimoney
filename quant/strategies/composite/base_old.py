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
    """分层策略组合基类。

    该组合只做“编排 (orchestration)”：
      1. 调用选股策略 selection.select -> 得到候选标的列表
      2. 对每个标的调用入场策略 entry.generate -> 收集入场信号 (允许 0..n 条/标的)
      3. 回测循环里由外部调用 evaluate_exit -> 调用 exit_rule.evaluate

    设计目标：
      - 解耦：三个策略互不依赖，便于替换 / 复用 / 组合
      - 可追踪：记录各层策略名称与参数快照，提升复现性
      - 轻量：不引入复杂事件系统；保持最小接口

    参数:
      selection: 选股策略实例，需实现 select(market_data) -> List[str]
      entry: 入场策略实例，需实现 generate(symbol, df) -> List[signal]
      exit_rule: 卖出策略实例，需实现 evaluate(position, bar) -> ExitDecision
      name: 组合名称（若上层未指定，可用各组件名称拼接）
    """

    def __init__(self, selection, entry, exit_rule, name: str):
        self.selection = selection
        self.entry = entry
        self.exit_rule = exit_rule
        self.name = name

        # 记录组件名称（若组件本身无 name 属性则回退其类名）
        self.selection_name = getattr(selection, 'name', selection.__class__.__name__)
        self.entry_name = getattr(entry, 'name', entry.__class__.__name__)
        self.exit_name = getattr(exit_rule, 'name', exit_rule.__class__.__name__)

        # 参数快照（便于日志 / 结果输出 / 序列化）
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
            # 给信号附加层信息（可协助审计 / Debug）
            for sig in sym_signals:
                sig.setdefault('meta', {})
                sig['meta'].setdefault('selection', self.selection_name)
                sig['meta'].setdefault('entry', self.entry_name)
            signals.extend(sym_signals)
        return signals

    def evaluate_exit(self, position: Dict[str, Any], bar: Dict[str, Any]):
        return self.exit_rule.evaluate(position, bar)

    # ---------- Introspection / Helpers ----------
    def to_dict(self) -> Dict[str, Any]:  # pragma: no cover - 纯数据导出
        return dict(self.config)

    def summary(self) -> str:  # pragma: no cover
        return (f"CompositeStrategy(name={self.name}, selection={self.selection_name}, "
                f"entry={self.entry_name}, exit={self.exit_name})")

    def __repr__(self) -> str:  # pragma: no cover
        return self.summary()

    # 选股详情（若 selection 支持）
    def selection_details(self, market_data: Dict[str, pd.DataFrame]) -> List[SelectionResult]:  # pragma: no cover
        sel = getattr(self.selection, 'select_with_details', None)
        if callable(sel):
            return sel(market_data)
        # 回退包装
        symbols = self.selection.select(market_data)
        return [SelectionResult(symbol=s) for s in symbols]

    # ---------- Factory Helpers ----------
    @classmethod
    def from_names(cls,
                    selection_name: str,
                    entry_name: str,
                    exit_name: str,
                    selection_params: Optional[Dict[str, Any]] = None,
                    entry_params: Optional[Dict[str, Any]] = None,
                    exit_params: Optional[Dict[str, Any]] = None,
                    name: Optional[str] = None) -> 'CompositeStrategy':  # pragma: no cover - thin wrapper
        """基于注册名快速构建组合。延迟导入避免循环依赖。"""
        from strategies.selection.registry import get_selection  # local import
        from strategies.entry.registry import get_entry
        from strategies.exit.registry import get_exit
        sel = get_selection(selection_name, params=selection_params)
        ent = get_entry(entry_name, params=entry_params)
        ex = get_exit(exit_name, params=exit_params)
        composite_name = name or f"Composite[sel={selection_name}|entry={entry_name}|exit={exit_name}]"
        return cls(sel, ent, ex, composite_name)
