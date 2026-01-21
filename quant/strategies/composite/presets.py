from __future__ import annotations

"""预设策略组合配置（完整四层：selection - entry - exit - execution）。

提供一些经过测试的策略组合预设，用户可以直接使用或作为参考。
"""

from typing import Dict, Any


STRATEGY_PRESETS: Dict[str, Dict[str, Any]] = {
    # 默认基础策略
    "default": {
        "selection": "hs300_top_weight",
        "entry": "b1",
        "exit": "time",
        "execution": "next_open",
        "selection_params": {"top_n": 20},
        "entry_params": {"j_threshold": 13},
        "exit_params": {"max_holding_days": 10},
        "description": "沪深300权重Top20 + 日KDJ(J<13) + 持有10天 - T+1开盘执行"
    },
    
    # T+1开盘执行策略
    "b1_tplus1": {
        "selection": "b1",
        "entry": "b1",
        "exit": "fixed",
        "execution": "next_open",
        "selection_params": {},
        "entry_params": {},
        "exit_params": {},
        "description": "B1策略 - T+1开盘执行"
    },
    
    # 追踪止损策略
    "b1_trailing": {
        "selection": "b1",
        "entry": "b1",
        "exit": "trailing",
        "execution": "next_open",
        "selection_params": {},
        "entry_params": {},
        "exit_params": {"trailing_pct": 0.08},
        "description": "B1策略 - 追踪止损8%"
    },
    
    # 高级退出策略
    "b1_advanced": {
        "selection": "b1",
        "entry": "b1",
        "exit": "advanced",
        "execution": "next_open",
        "selection_params": {"j_threshold": -10, "big_positive_pct": 0.06},
        "entry_params": {"take_profit_pct": 0.25},
        "exit_params": {"trailing_pct": 0.10, "max_holding_days": 20},
        "description": "B1高级策略 - 组合追踪止损和时间退出"
    },
    
    # 激进策略
    "b1_aggressive": {
        "selection": "b1",
        "entry": "b1",
        "exit": "trailing",
        "execution": "close",
        "selection_params": {"j_threshold": -5, "big_positive_pct": 0.04},
        "entry_params": {"take_profit_pct": 0.35},
        "exit_params": {"trailing_pct": 0.12},
        "description": "激进B1策略 - 放宽选股条件"
    },
    
    # 保守策略
    "b1_conservative": {
        "selection": "b1",
        "entry": "b1",
        "exit": "fixed",
        "execution": "next_open",
        "selection_params": {"j_threshold": -15, "big_positive_pct": 0.07, "ma_window": 30},
        "entry_params": {"stop_loss_pct": 0.08, "take_profit_pct": 0.20},
        "exit_params": {"stop_loss": 0.08, "target_price_pct": 0.20},
        "description": "保守B1策略 - 严格选股"
    },
}


def get_preset_config(name: str) -> Dict[str, Any]:
    """获取预设策略配置"""
    if name not in STRATEGY_PRESETS:
        available = ', '.join(STRATEGY_PRESETS.keys())
        raise ValueError(f"未找到预设策略: {name}\n可用预设: {available}")
    return STRATEGY_PRESETS[name].copy()


def list_presets() -> Dict[str, str]:
    """列出所有可用的预设策略及其描述"""
    return {name: config["description"] for name, config in STRATEGY_PRESETS.items()}


__all__ = ['STRATEGY_PRESETS', 'get_preset_config', 'list_presets']
