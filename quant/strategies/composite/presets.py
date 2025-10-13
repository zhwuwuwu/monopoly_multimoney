from __future__ import annotations

PRESET_COMPOSITES = {
    'b1_default': {
        'selection': ('b1', None),
        'entry': ('b1', None),
        'exit': ('fixed', None),
        'execution_model': 'next_open',
        'composite_name': 'B1[default]',
    },
    'b1_close_fixed': {
        'selection': ('b1', None),
        'entry': ('b1', None),
        'exit': ('fixed', None),
        'execution_model': 'close',
        'composite_name': 'B1[close_fixed]',
    },
    'b1_trailing': {
        'selection': ('b1', None),
        'entry': ('b1', None),
        'exit': ('trailing', {'trailing_pct': 0.1}),
        'execution_model': 'next_open',
        'composite_name': 'B1[trailing]',
    },
    # 新增：指数/ETF 权重前20 + B1 入场 + 固定风险退出
    'index_contrib_b1_fixed': {
        'selection': ('index_contribute_select', {'source_type': 'index', 'code': '000300', 'top_k': 20}),
        'entry': ('b1', None),
        'exit': ('fixed', None),
        'execution_model': 'next_open',
        'composite_name': 'IdxContrib(000300)_B1',
    },
}

def get_preset_config(name: str):
    key = name.lower()
    if key not in PRESET_COMPOSITES:
        raise ValueError(f"未知组合预设: {name}")
    return PRESET_COMPOSITES[key]

__all__ = ['PRESET_COMPOSITES', 'get_preset_config']
