"""Utility / helper functions for the Smart Plant Monitoring dashboard."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd


def utcNow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def latestValue(series: pd.Series, default: Optional[float] = None) -> Optional[float]:
    if series is None or series.empty:
        return default
    val = series.iloc[0]
    if pd.isna(val):
        return default
    return float(val)


def percentOfRange(value: Optional[float], lo: float, hi: float) -> int:
    if value is None or hi == lo:
        return 0
    pct = (value - lo) / (hi - lo) * 100
    return int(max(0, min(100, pct)))


def imageDataUri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"
