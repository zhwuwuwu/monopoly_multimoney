from __future__ import annotations

from typing import Dict, Any, List, Callable, Optional
import pandas as pd

from .portfolio import Portfolio
from util.market_data_handler import MarketDataHandler


class Backtester:
    """Configurable backtester supporting basic position sizing and costs.

    NOT a full featured engine yet; intentionally lightweight.
    """

    def __init__(self,
                 data_handler: MarketDataHandler,
                 strategy,
                 initial_capital: float = 1_000_000,
                 max_positions: int = 5,
                 lookback_days: int = 180,
                 commission_rate: float = 0.0005,  # 单边手续费
                 slippage_bp: float = 5.0,          # 成交滑点 基点(basis points)
                 position_sizer: Optional[Callable[[float, int, float], int]] = None):
        self.data_handler = data_handler
        self.strategy = strategy
        self.initial_capital = float(initial_capital)
        self.max_positions = max_positions
        self.lookback_days = lookback_days
        self.commission_rate = commission_rate
        self.slippage_bp = slippage_bp
        self.portfolio = Portfolio(initial_capital)
        self.position_sizer = position_sizer or self.equal_weight_sizer
        self.trades = []  # type: List[Dict[str, Any]]
        self.market_cache = {}  # type: Dict[str, Any]
        # pending entry signals waiting for future execution (e.g., T+1 open)
        self.pending_entries = []  # type: List[Dict[str, Any]]

    # --- sizing helpers ---
    def equal_weight_sizer(self, cash: float, remaining_slots: int, price: float) -> int:
        alloc = cash / max(1, remaining_slots)
        shares = int(alloc // price)
        return shares

    def _apply_slippage(self, raw_price: float, side: str) -> float:
        adj = raw_price * (self.slippage_bp / 10000.0)
        return raw_price + (adj if side == 'BUY' else -adj)

    def _apply_commission(self, gross: float) -> float:
        return gross * self.commission_rate

    def _load_daily_universe(self, dt: pd.Timestamp, symbols: List[str]) -> Dict[str, Any]:
        market_data: Dict[str, Any] = {}
        for sym in symbols:
            df = self.market_cache.get(sym)
            if df is None or dt not in df.index:
                df = self.data_handler.get_stock_data(sym, (dt - pd.Timedelta(days=self.lookback_days)).strftime('%Y%m%d'), dt.strftime('%Y%m%d'))
                if df is None:
                    continue
                self.market_cache[sym] = df
            if dt in self.market_cache[sym].index:
                market_data[sym] = self.market_cache[sym]
        return market_data

    def _process_exits(self, dt: pd.Timestamp, market_data: Dict[str, Any]):
        to_remove = []
        for sym, pos in list(self.portfolio.positions.items()):
            df = market_data.get(sym)
            if df is None or dt not in df.index:
                continue
            bar_close = float(df.loc[dt, 'close'])
            # update highest_price for trailing styles (non-intrusive)
            hp = pos.get('highest_price')
            if hp is None or bar_close > hp:
                pos['highest_price'] = bar_close
            decision = self.strategy.evaluate_exit(pos, {"date": dt, "close": bar_close})
            if decision.exit:
                exec_price = self._apply_slippage(decision.price or bar_close, 'SELL')
                gross = exec_price * pos['shares']
                commission = self._apply_commission(gross)
                self.portfolio.cash += gross - commission
                pnl = (exec_price - pos['entry_price']) * pos['shares'] - commission
                self.trades.append({
                    'date': dt,
                    'symbol': sym,
                    'action': 'SELL',
                    'price': exec_price,
                    'shares': pos['shares'],
                    'pnl': pnl,
                    'commission': commission,
                    'holding_days': (dt - pos['entry_date']).days,
                    'reason': decision.reason,
                })
                to_remove.append(sym)
        for sym in to_remove:
            self.portfolio.remove_position(sym)

    def _execute_entry(self, dt: pd.Timestamp, sym: str, df: pd.DataFrame, sig: Dict[str, Any], price_type: str, remaining_slots: int) -> int:
        """Execute a single entry order, returns updated remaining_slots (may be unchanged)."""
        if sym in self.portfolio.positions:
            return remaining_slots
        if dt not in df.index:
            return remaining_slots
        if remaining_slots <= 0:
            return remaining_slots
        if price_type == 'open' and 'open' in df.columns:
            raw_price = float(df.loc[dt, 'open'])
        else:
            raw_price = float(df.loc[dt, 'close'])
        exec_price = self._apply_slippage(raw_price, 'BUY')
        shares = self.position_sizer(self.portfolio.cash, remaining_slots, exec_price)
        if shares <= 0:
            return remaining_slots
        gross_cost = shares * exec_price
        commission = self._apply_commission(gross_cost)
        total_cost = gross_cost + commission
        if total_cost > self.portfolio.cash:
            return remaining_slots
        self.portfolio.cash -= total_cost
        self.portfolio.add_position(sym, shares, exec_price, {
            'stop_loss': sig.get('stop_loss'),
            'target_price': sig.get('target_price'),
            'entry_date': dt,
            'highest_price': exec_price,  # seed for trailing logic
        })
        self.trades.append({
            'date': dt,
            'symbol': sym,
            'action': 'BUY',
            'price': exec_price,
            'shares': shares,
            'pnl': 0.0,
            'commission': commission,
            'reason': sig.get('meta', {}).get('execution', 'entry'),
        })
        return remaining_slots - 1

    def _process_entries(self, dt: pd.Timestamp, market_data: Dict[str, Any]):
        remaining_slots = self.max_positions - len(self.portfolio.positions)
        if remaining_slots <= 0:
            return
        entry_signals = self.strategy.generate_entries(market_data)
        # separate future (pending) vs immediate signals
        for sig in entry_signals:
            sym = sig['symbol']
            df = market_data.get(sym)
            if df is None:
                continue
            exec_date = sig.get('exec_date')
            exec_price_type = sig.get('exec_price_type', 'close')
            if exec_date and exec_date != dt:
                # future execution; store if not duplicate
                self.pending_entries.append({**sig, 'exec_price_type': exec_price_type})
                continue
            # immediate execution (same day close by default)
            remaining_slots = self._execute_entry(dt, sym, df, sig, exec_price_type, remaining_slots)
            if remaining_slots <= 0:
                break

    def _process_pending_entries(self, dt: pd.Timestamp, market_data: Dict[str, Any]):
        if not self.pending_entries:
            return
        still_pending = []
        remaining_slots = self.max_positions - len(self.portfolio.positions)
        for sig in self.pending_entries:
            if remaining_slots <= 0:
                still_pending.append(sig)
                continue
            if sig.get('exec_date') != dt:
                still_pending.append(sig)
                continue
            sym = sig['symbol']
            df = market_data.get(sym)
            if df is None:
                # data unavailable keep waiting (or could drop)
                still_pending.append(sig)
                continue
            remaining_slots = self._execute_entry(dt, sym, df, sig, sig.get('exec_price_type', 'open'), remaining_slots)
        self.pending_entries = still_pending

    def run(self, start_date: str, end_date: str, universe_size: int = 100):  # pragma: no cover
        dates = pd.date_range(start_date, end_date, freq='B')
        symbols = self.data_handler.get_hs300_components()[:universe_size]
        for dt in dates:
            market_data = self._load_daily_universe(dt, symbols)
            # 1. 先处理 T+1 等待的开盘买入
            self._process_pending_entries(dt, market_data)
            # 2. 处理持仓退出（按收盘逻辑）
            self._process_exits(dt, market_data)
            # 3. 生成新的入场信号（部分为当日收盘成交，部分进入 pending）
            self._process_entries(dt, market_data)
            # mark to market
            close_prices = {s: float(df.loc[dt, 'close']) for s, df in market_data.items() if dt in df.index}
            self.portfolio.mark_to_market(dt, close_prices)
        return {"history": self.portfolio.history, "trades": self.trades, "strategy_config": getattr(self.strategy, 'to_dict', lambda: {} )()}
