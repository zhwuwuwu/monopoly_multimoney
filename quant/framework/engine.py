from __future__ import annotations

from strategies.composite.registry import get_strategy
from util.market_data_handler import MarketDataHandler
from .backtester import Backtester
from .performance import compute_equity_metrics, compute_trade_metrics, merge_metrics
from typing import List, Dict, Any


class BacktestEngine:
    def __init__(self, strategy_name: str = "b1", strategy_kwargs=None, initial_capital=1_000_000):
        self.data_handler = MarketDataHandler()
        self.strategy_name = strategy_name
        self.strategy_kwargs = strategy_kwargs or {}
        self.initial_capital = initial_capital

    def build_strategy(self):
        return get_strategy(self.strategy_name, params=self.strategy_kwargs)

    def run(self, start_date: str, end_date: str, **bt_kwargs):  # pragma: no cover
        strategy = self.build_strategy()
        bt = Backtester(self.data_handler, strategy, initial_capital=self.initial_capital, **bt_kwargs)
        raw = bt.run(start_date, end_date, universe_size=bt_kwargs.get('universe_size', 100))
        import pandas as pd
        history_df = pd.DataFrame(raw['history'])
        trades_df = pd.DataFrame(raw['trades']) if raw['trades'] else pd.DataFrame(columns=['date'])
        eq_metrics = compute_equity_metrics(history_df.rename(columns={'date': 'date'})) if not history_df.empty else {}
        trade_metrics = compute_trade_metrics(raw['trades'])
        metrics = merge_metrics(eq_metrics, trade_metrics)
        return {
            'history': history_df,
            'trades': trades_df,
            'metrics': metrics,
            'params': {
                'strategy': self.strategy_name,
                **self.strategy_kwargs,
                **bt_kwargs
            },
            'strategy_config': raw.get('strategy_config')
        }


def run_parallel_experiments(configs: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:  # pragma: no cover
    results = []
    for cfg in configs:
        engine = BacktestEngine(strategy_name=cfg.get('strategy', 'b1'),
                                strategy_kwargs=cfg.get('strategy_params'),
                                initial_capital=cfg.get('initial_capital', 1_000_000))
        res = engine.run(start_date, end_date, **{k: v for k, v in cfg.items() if k not in {'strategy', 'strategy_params', 'initial_capital'}})
        results.append(res)
    return results

__all__ = ['BacktestEngine', 'run_parallel_experiments']
