from __future__ import annotations

from ..selection.b1_selection import B1Selection
from ..entry.b1_entry import B1Entry
from ..entry.tplus1_entry import B1EntryTPlus1
from ..exit.fixed_risk_exit import FixedRiskExit
from ..exit.advanced_exit import TimeBasedExit, TrailingStopExit, AdvancedExit
from .base import CompositeStrategy


class B1CompositeStrategy(CompositeStrategy):
    """B1 专用组合策略类。

    特点：
      - 选股固定使用 B1Selection
      - 入场默认使用 T+1 开盘买入（B1EntryTPlus1），可切换为 same-day 收盘 (B1Entry)
      - 卖出策略可选 fixed / time / trailing / advanced

    参数:
      entry_execution:   same_close | t+1 / tplus1 / next_open (默认 t+1)
      exit_type:         fixed | time | trailing | advanced
      exit_args:         dict 传递给对应 exit 构造器
      name:              自定义策略名称，未提供时根据配置生成
      **shared_params:   其余参数同时传给 B1Selection 与 入场策略
    """

    def __init__(self,
                 entry_execution: str = 't+1',
                 exit_type: str = 'fixed',
                 exit_args: dict | None = None,
                 name: str | None = None,
                 **shared_params):
        exit_type_l = (exit_type or 'fixed').lower()
        entry_exec_l = (entry_execution or 't+1').lower()

        selection = B1Selection(params=shared_params or None)
        if entry_exec_l in ('t+1', 'tplus1', 'next_open'):
            entry = B1EntryTPlus1(params=shared_params or None)
        else:
            entry = B1Entry(params=shared_params or None)

        exit_args = exit_args or {}
        if exit_type_l == 'fixed':
            exit_rule = FixedRiskExit()
        elif exit_type_l == 'time':
            exit_rule = TimeBasedExit(**exit_args)
        elif exit_type_l == 'trailing':
            exit_rule = TrailingStopExit(**exit_args)
        elif exit_type_l == 'advanced':
            exit_rule = AdvancedExit(**exit_args)
        else:
            raise ValueError(f"未知 exit_type: {exit_type}")

        composite_name = name or f"B1[{entry_exec_l}|{exit_type_l}]"
        super().__init__(selection, entry, exit_rule, composite_name)


def build_b1_composite(params=None) -> CompositeStrategy:  # 兼容旧接口
    params = params or {}
    return B1CompositeStrategy(
        entry_execution=params.get('entry_execution', 'same_close'),
        exit_type=params.get('exit_type', 'fixed'),
        exit_args=params.get('exit_args'),
        **{k: v for k, v in params.items() if k not in {'entry_execution', 'exit_type', 'exit_args'}}
    )

