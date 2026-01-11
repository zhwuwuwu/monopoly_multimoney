"""Shared dataclasses and type definitions for rnotegen agents."""

from dataclasses import dataclass
from typing import List


@dataclass
class Material:
    """Represents source material for content generation."""
    title: str
    content: str
    source: str
    type: str  # news, historical, theoretical, etc.
    reliability_score: float = 0.0


@dataclass
class GeneratedContent:
    """Represents generated article content."""
    title: str
    content: str
    hashtags: List[str]
    summary: str
    word_count: int
    sources: List[str]
    fact_checked: bool = False
