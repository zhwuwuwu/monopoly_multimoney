"""Common reusable candle/indicator condition helpers for strategies.

These functions encapsulate primitive pattern or threshold checks that were
previously duplicated between selection (`B1Selection`) and entry (`B1Entry`).

Design goals:
  * Stateless pure functions (easy to unit test / cache / reuse)
  * Defensive boundary checks (return False when data insufficient)
  * Clear naming conventions: `is_*` returning bool

NOTE: They purposely do NOT mutate input DataFrames.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd

Number = float | int


def is_kdj_low(df: pd.DataFrame, i: int, j_threshold: Number) -> bool:
    """KDJ low condition used as oversold signal.

    Requirements:
      * Column 'J' present
      * Index i within bounds
    """
    if 'J' not in df.columns or i >= len(df) or i < 0:
        return False
    try:
        return df['J'].iloc[i] < j_threshold
    except Exception:
        return False


def is_bottom_pattern(df: pd.DataFrame, i: int) -> bool:
    """Simple bottom-ish 3-bar pattern (current bar narrower / lower).

    Logic (current index = i):
      * Need at least 2 prior bars
      * current low < previous two lows
      * current high < previous two highs (contracting / weak rebound)
    """
    if i < 2:
        return False
    try:
        curr_low = df['low'].iloc[i]
        curr_high = df['high'].iloc[i]
        return (
            curr_low < df['low'].iloc[i - 1]
            and curr_low < df['low'].iloc[i - 2]
            and curr_high < df['high'].iloc[i - 1]
            and curr_high < df['high'].iloc[i - 2]
        )
    except Exception:
        return False


def is_big_positive(df: pd.DataFrame, i: int, pct_threshold: Number) -> bool:
    """Large positive candle confirmation.

    Definition: close > open * (1 + pct_threshold)
    """
    if i < 0 or i >= len(df):
        return False
    try:
        return df['close'].iloc[i] > df['open'].iloc[i] * (1 + pct_threshold)
    except Exception:
        return False


def is_above_ma(df: pd.DataFrame, i: int, window: int) -> bool:
    """Price above simple moving average(window)."""
    if window <= 0 or len(df) <= i or len(df) < window:
        return False
    try:
        ma = df['close'].rolling(window=window).mean().iloc[i]
        return df['close'].iloc[i] > ma
    except Exception:
        return False


def is_volume_surge(df: pd.DataFrame, i: int, ratio: Number, lookback: int = 5) -> bool:
    """Volume spike: current volume > avg(volume[-lookback:]) * ratio."""
    if 'volume' not in df.columns or i < lookback:
        return False
    try:
        avg_vol = df['volume'].iloc[i - lookback:i].mean()
        return df['volume'].iloc[i] > avg_vol * ratio
    except Exception:
        return False


def is_volume_shrink(df: pd.DataFrame, i: int, ratio: Number, lookback: int = 5) -> bool:
    """Volume contraction: current volume < avg(volume[-lookback:]) / ratio."""
    if 'volume' not in df.columns or i < lookback:
        return False
    try:
        avg_vol = df['volume'].iloc[i - lookback:i].mean()
        return df['volume'].iloc[i] < avg_vol / ratio
    except Exception:
        return False


def is_macd_golden_cross(df: pd.DataFrame, i: int) -> bool:
    """Placeholder MACD golden cross detection.

    Requires a column 'MACD'. This repo currently does not compute MACD,
    so this will typically return False unless user pre-computes.
    Condition: MACD[i-1] < 0 and MACD[i] > 0
    """
    if 'MACD' not in df.columns or i < 1:
        return False
    try:
        return df['MACD'].iloc[i - 1] < 0 and df['MACD'].iloc[i] > 0
    except Exception:
        return False


__all__ = [
    'is_kdj_low',
    'is_bottom_pattern',
    'is_big_positive',
    'is_above_ma',
    'is_volume_surge',
    'is_volume_shrink',
    'is_macd_golden_cross',
]
