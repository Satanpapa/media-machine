"""Agents package for Media Machine."""

from .trend_detector import TrendDetector
from .writer import Writer
from .hype_optimizer import HypeOptimizer
from .critic import Critic
from .judge import Judge
from .analyst import Analyst
from .strategist import Strategist
from .publisher import Publisher, Monetizer

__all__ = [
    "TrendDetector",
    "Writer",
    "HypeOptimizer",
    "Critic",
    "Judge",
    "Analyst",
    "Strategist",
    "Publisher",
    "Monetizer"
]
