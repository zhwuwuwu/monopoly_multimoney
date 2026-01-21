"""B1 Selection 变体构建器

提供不同条件组合 / 参数配置的便捷工厂。
"""
from __future__ import annotations

from typing import Dict

from .b1_selection import B1Selection


def build_b1_selection_variant(name: str) -> B1Selection:
    name = name.lower()
    # 基础参数可进一步扩展
    base_params = {}

    # 默认激活条件（在 B1Selection 内部也有一份；这里覆盖）
    if name == "default":
        active = {
            "kdj_condition": True,
            "bottom_pattern_condition": False,
            "big_positive_condition": False,
            "above_ma_condition": False,
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False,
        }
        logic = "AND"
    elif name == "b1+":  # 与 legacy 类似的更严格组合
        active = {
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False,
        }
        logic = "AND"
    elif name == "volume_surge":
        active = {
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": True,
            "volume_shrink_condition": False,
            "macd_golden_cross": False,
        }
        base_params["volume_ratio"] = 1.5
        logic = "AND"
    elif name == "loose":
        active = {
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": False,
            "volume_shrink_condition": False,
            "macd_golden_cross": False,
        }
        base_params["j_threshold"] = -5
        logic = "OR"
    elif name == "weighted":  # 暂未实现加权逻辑，这里先退化为 AND 全部
        active = {
            "kdj_condition": True,
            "bottom_pattern_condition": True,
            "big_positive_condition": True,
            "above_ma_condition": True,
            "volume_surge_condition": True,
            "volume_shrink_condition": False,
            "macd_golden_cross": False,
        }
        logic = "AND"
    else:
        raise ValueError(f"未知 B1 变体: {name}")

    return B1Selection(params=base_params, active_conditions=active, logic=logic)


__all__ = ["build_b1_selection_variant"]
