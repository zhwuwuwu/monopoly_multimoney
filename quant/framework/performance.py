from __future__ import annotations

"""Performance metrics utilities for backtest results.

Keeps dependencies minimal (pandas, numpy, matplotlib optional in visualize module).
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import pandas as pd
import numpy as np


@dataclass
class TradeRecord:
    symbol: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    return_pct: float
    holding_days: int
    reason: str


def compute_equity_metrics(equity_df: pd.DataFrame, trading_days_per_year: int = 252) -> Dict[str, Any]:
    if equity_df.empty:
        return {}
    equity_df = equity_df.sort_values('date')
    equity_df['equity'] = equity_df['total_value']
    equity_df['returns'] = equity_df['equity'].pct_change().fillna(0)
    total_return = equity_df['equity'].iloc[-1] / equity_df['equity'].iloc[0] - 1
    n_days = len(equity_df)
    cagr = (1 + total_return) ** (trading_days_per_year / max(1, n_days)) - 1 if n_days > 1 else 0
    vol = equity_df['returns'].std() * np.sqrt(trading_days_per_year) if n_days > 2 else 0
    sharpe = (equity_df['returns'].mean() * trading_days_per_year) / vol if vol > 0 else 0

    # Max drawdown
    cumulative = equity_df['equity']
    rolling_max = cumulative.cummax()
    drawdowns = (cumulative / rolling_max - 1)
    max_dd = drawdowns.min()
    dd_end_idx = drawdowns.idxmin()
    if dd_end_idx is not None:
        dd_start_idx = (cumulative[:dd_end_idx].idxmax() if dd_end_idx in cumulative.index else cumulative.idxmax())
    else:
        dd_start_idx = None

    return {
        'total_return': total_return,
        'cagr': cagr,
        'volatility': vol,
        'sharpe': sharpe,
        'max_drawdown': max_dd,
        'max_drawdown_start': equity_df.loc[dd_start_idx, 'date'] if dd_start_idx is not None else None,
        'max_drawdown_end': equity_df.loc[dd_end_idx, 'date'] if dd_end_idx is not None else None,
        'num_days': n_days,
    }


def compute_trade_metrics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {}
    df = pd.DataFrame(trades)
    closed = df[df['action'] == 'SELL']
    if closed.empty:
        return {'open_trades': len(df[df['action'] == 'BUY'])}
    wins = closed[closed['pnl'] > 0]
    losses = closed[closed['pnl'] <= 0]
    gross_profit = wins['pnl'].sum()
    gross_loss = losses['pnl'].sum()
    profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0 else float('inf')
    avg_gain = wins['pnl'].mean() if not wins.empty else 0
    avg_loss = losses['pnl'].mean() if not losses.empty else 0
    win_rate = len(wins) / len(closed) if len(closed) > 0 else 0
    avg_holding = closed['holding_days'].mean() if 'holding_days' in closed else None
    return {
        'trades_total': len(closed),
        'win_rate': win_rate,
        'avg_gain': avg_gain,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'avg_holding_days': avg_holding,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'net_profit': closed['pnl'].sum(),
    }


def merge_metrics(equity_metrics: Dict[str, Any], trade_metrics: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    out.update(equity_metrics)
    out.update(trade_metrics)
    return out


__all__ = [
    'compute_equity_metrics',
    'compute_trade_metrics',
    'merge_metrics',
    'TradeRecord',
]