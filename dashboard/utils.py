"""Utility / helper functions for the Smart Plant Monitoring dashboard."""

from __future__ import annotations

import base64
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

# Use the non-interactive Agg backend before importing pyplot.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from PIL import Image  # noqa: E402


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


# ───────────────────────────── Heatmap utilities ─────────────────────────────

_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "plant_heat",
    [
        (0.0, (0.0, 0.0, 0.0, 0.0)),
        (0.3, (1.0, 0.85, 0.0, 0.45)),
        (0.7, (1.0, 0.45, 0.0, 0.7)),
        (1.0, (0.85, 0.0, 0.0, 0.9)),
    ],
)


def parsePixelPoints(value) -> list[tuple[float, float]]:
    """Parse a JSON array of [x, y] pixel coordinates from the heatmap column."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    text = value if isinstance(value, str) else str(value)
    text = text.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    points: list[tuple[float, float]] = []
    if isinstance(parsed, list):
        for entry in parsed:
            if (
                isinstance(entry, (list, tuple))
                and len(entry) >= 2
                and all(isinstance(v, (int, float)) for v in entry[:2])
            ):
                points.append((float(entry[0]), float(entry[1])))
    return points


def _gaussianDensity(
    width: int,
    height: int,
    points: Iterable[tuple[float, float]],
    sigma: float,
) -> np.ndarray:
    """Build a 2D density map from points using Gaussian splats."""
    grid = np.zeros((height, width), dtype=np.float32)
    pts = [(x, y) for x, y in points if 0 <= x < width and 0 <= y < height]
    if not pts:
        return grid
    radius = int(np.ceil(3.0 * sigma))
    for x, y in pts:
        x0 = max(0, int(x) - radius)
        x1 = min(width, int(x) + radius + 1)
        y0 = max(0, int(y) - radius)
        y1 = min(height, int(y) + radius + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        xs = np.arange(x0, x1, dtype=np.float32)
        ys = np.arange(y0, y1, dtype=np.float32)
        xx, yy = np.meshgrid(xs, ys)
        d2 = (xx - x) ** 2 + (yy - y) ** 2
        grid[y0:y1, x0:x1] += np.exp(-d2 / (2.0 * sigma * sigma))
    peak = grid.max()
    if peak > 0:
        grid /= peak
    return grid


def renderHeatmapOverlay(
    imagePath: Path,
    points: list[tuple[float, float]],
) -> Optional[str]:
    """Render a heatmap overlay on the leaf image.

    Returns a `data:image/png;base64,...` URI, or None if the image
    cannot be loaded.
    """
    try:
        img = Image.open(imagePath).convert("RGB")
    except (FileNotFoundError, OSError):
        return None

    width, height = img.size
    sigma = max(20.0, min(width, height) * 0.06)
    density = _gaussianDensity(width, height, points, sigma=sigma)

    fig = plt.figure(figsize=(width / 100, height / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(np.asarray(img))
    if density.any():
        ax.imshow(
            density,
            cmap=_HEATMAP_CMAP,
            vmin=0.0,
            vmax=1.0,
            interpolation="bilinear",
        )
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.scatter(
            xs, ys, s=40, facecolors="none", edgecolors="white", linewidths=1.5
        )
    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.axis("off")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
