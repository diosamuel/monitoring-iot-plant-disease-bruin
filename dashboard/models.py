"""Dataclass models for the Smart Plant Monitoring dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Metrics:
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    soilRaw: Optional[float] = None
    soilPct: Optional[int] = None
    healthScore: int = 0
    unhealthyPct: float = 0.0


@dataclass
class VisionInsight:
    available: bool = False
    filename: str = ""
    eventTime: Optional[pd.Timestamp] = None
    status: str = "unknown"
    isHealthy: bool = False
    badge: str = "WARNING"
    title: str = "Inspection Needed"
    confidencePct: int = 0
    severity: Optional[float] = None
    summary: str = "No summary available."
    recommendations: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
