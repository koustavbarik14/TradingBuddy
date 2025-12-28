"""TradingBuddy package wrapper.

This exposes the main helper classes from the existing root-level modules so other modules can
import them as `from tradingbuddy import DataIngestion, PatternDetection` for clearer, absolute imports.
"""

from .core import DataIngestion, PatternDetection

__all__ = ["DataIngestion", "PatternDetection"]
