from __future__ import annotations

"""通用自定义组合策略构造函数，减少与 B1 专用构造的重复。

核心目标：用户在回测入口直接提供各层名称与参数，得到实例；默认策略名称
为 customized_strategy。使用场景：命令行 / 配置文件动态装配。
"""

from typing import Optional
from ..selection.registry import get_selection
from ..entry.registry import get_entry
from ..exit.registry import get_exit
from .base import CompositeStrategy


def build_custom_strategy(
    selection_name: str = 'b1',
    entry_name: str = 'b1',
    exit_name: str = 'fixed',
    selection_params: Optional[dict] = None,
    entry_params: Optional[dict] = None,
    exit_params: Optional[dict] = None,
    name: str | None = None,
    default_name: str = 'customized_strategy',
):
    """通用组合策略装配。

    若未提供 name，则：
      1) 若 default_name 非空，使用 default_name
      2) 否则拼接三层名称
    """
    selection = get_selection(selection_name, params=selection_params)
    entry = get_entry(entry_name, params=entry_params)
    exit_rule = get_exit(exit_name, params=exit_params)
    if name:
        composite_name = name
    else:
        composite_name = default_name or f"Composite[sel={selection_name}|entry={entry_name}|exit={exit_name}]"
    return CompositeStrategy(selection, entry, exit_rule, composite_name)
