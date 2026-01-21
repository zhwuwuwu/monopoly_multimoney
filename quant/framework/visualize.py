from __future__ import annotations

from typing import List, Dict, Any
import pandas as pd

try:  # optional dependency
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore


def plot_equity(history: pd.DataFrame, save_path: str | None = None):  # pragma: no cover
    if plt is None:
        print('[visualize] matplotlib not available.')
        return
    if history.empty:
        print('[visualize] empty history.')
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(history['date'], history['total_value'], label='Equity')
    ax.set_title('Equity Curve')
    ax.grid(alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'[visualize] equity saved: {save_path}')
    else:
        plt.show()


def compare_equity(experiments: List[Dict[str, Any]], save_path: str | None = None):  # pragma: no cover
    if plt is None:
        print('[visualize] matplotlib not available.')
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    for res in experiments:
        hist = res['history']
        if hist.empty:
            continue
        label = res['params'].get('label') or f"{res['params'].get('strategy')}"
        ax.plot(hist['date'], hist['total_value'], label=label)
    ax.set_title('Equity Comparison')
    ax.grid(alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f'[visualize] comparison saved: {save_path}')
    else:
        plt.show()


__all__ = ['plot_equity', 'compare_equity']