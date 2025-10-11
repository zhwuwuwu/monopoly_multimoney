from __future__ import annotations

from typing import Dict, Callable
from .b1_composite import build_b1_composite, B1CompositeStrategy
from .factory import build_custom_strategy


STRATEGY_BUILDERS: Dict[str, Callable] = {
    "b1": build_b1_composite,           # 保留快捷调用
    "custom": build_custom_strategy,    # 通用装配入口
    "layered": build_custom_strategy,   # 兼容旧名字
    "b1_class": lambda **kw: B1CompositeStrategy(**(kw.get('params') or {})),  # 可直接实例化类（兼容扩展）
}


def get_strategy(name: str, **kwargs):
    if name not in STRATEGY_BUILDERS:
        raise ValueError(f"未知策略: {name}")
    return STRATEGY_BUILDERS[name](**kwargs)
