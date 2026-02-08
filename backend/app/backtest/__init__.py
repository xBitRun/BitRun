"""Backtesting module for strategy simulation"""

from .engine import BacktestEngine, BacktestResult
from .data_provider import DataProvider, OHLCV
from .simulator import SimulatedTrader, SimulatedPosition

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "DataProvider",
    "OHLCV",
    "SimulatedPosition",
    "SimulatedTrader",
]
