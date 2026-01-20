from __future__ import annotations

"""通用四层策略工厂：selection - entry - exit - execution。

核心改进：
  1. 强制要求四层策略完整（selection/entry/exit/execution）
  2. 统一通过 factory 构建，移除其他构建方式
  3. 提供默认策略和验证机制
"""

from typing import Optional
from ..selection.registry import get_selection
from ..entry.registry import get_entry
from ..exit.registry import get_exit
from ..execution.registry import get_execution_model
from .base import CompositeStrategy


def build_custom_strategy(
    selection_name: str = 'b1',
    entry_name: str = 'b1',
    exit_name: str = 'fixed',
    execution_name: str = 'close',
    selection_params: Optional[dict] = None,
    entry_params: Optional[dict] = None,
    exit_params: Optional[dict] = None,
    execution_params: Optional[dict] = None,
    name: str | None = None,
    default_name: str = 'custom_strategy',
    validate: bool = True,
):
    """四层策略装配工厂（必须包含 selection/entry/exit/execution）。
    
    Args:
        selection_name: 选股策略名称
        entry_name: 入场策略名称
        exit_name: 退出策略名称
        execution_name: 执行模式名称（close/next_open/tplus1/vwap）
        selection_params: 选股策略参数
        entry_params: 入场策略参数
        exit_params: 退出策略参数
        execution_params: 执行模式参数（目前执行模式不需要参数）
        name: 策略名称
        default_name: 默认策略名称
        validate: 是否验证策略完整性
        
    Returns:
        CompositeStrategy: 完整的四层组合策略
        
    Raises:
        ValueError: 当策略配置不完整时
    """
    # 验证必要参数
    if validate:
        if not all([selection_name, entry_name, exit_name, execution_name]):
            raise ValueError(
                "策略配置不完整！必须提供四层策略：\n"
                f"  - selection: {selection_name or 'MISSING'}\n"
                f"  - entry: {entry_name or 'MISSING'}\n"
                f"  - exit: {exit_name or 'MISSING'}\n"
                f"  - execution: {execution_name or 'MISSING'}"
            )
    
    # 构建各层策略
    selection = get_selection(selection_name, params=selection_params)
    entry = get_entry(entry_name, params=entry_params)
    exit_rule = get_exit(exit_name, params=exit_params)
    execution_model = get_execution_model(execution_name)
    
    # 生成策略名称
    if name:
        composite_name = name
    else:
        composite_name = default_name or (
            f"{selection_name}_{entry_name}_{exit_name}_{execution_name}"
        )
    
    return CompositeStrategy(
        selection=selection,
        entry=entry,
        exit_rule=exit_rule,
        execution_model=execution_model,
        name=composite_name
    )


__all__ = ['build_custom_strategy']
