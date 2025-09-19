"""NACA airfoil generators."""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Tuple

import numpy as np


class InvalidNACACode(ValueError):
    """Raised when the provided NACA code cannot be parsed."""


def _parse_naca4(code: str) -> Tuple[float, float, float]:
    if len(code) != 4 or not code.isdigit():
        raise InvalidNACACode("NACA 4-digit codes must be four digits long.")
    m = int(code[0]) / 100.0
    p = int(code[1]) / 10.0
    t = int(code[2:]) / 100.0
    return m, p, t


@lru_cache(maxsize=128)
def naca4_coordinates(code: str, points_per_surface: int = 80) -> Dict[str, Dict[str, np.ndarray]]:
    """Generate cosine-spaced coordinates for a NACA 4-digit airfoil."""
    m, p, t = _parse_naca4(code)

    if points_per_surface < 3:
        raise ValueError("points_per_surface must be at least 3")

    beta = np.linspace(0.0, np.pi, points_per_surface)
    x = 0.5 * (1 - np.cos(beta))

    yt = 5 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1015 * x**4
    )

    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    if m > 0 and p > 0:
        mask = x < p
        yc[mask] = m / (p**2) * (2 * p * x[mask] - x[mask] ** 2)
        dyc_dx[mask] = 2 * m / (p**2) * (p - x[mask])
        mask = ~mask
        yc[mask] = m / ((1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x[mask] - x[mask] ** 2)
        dyc_dx[mask] = 2 * m / ((1 - p) ** 2) * (p - x[mask])

    theta = np.arctan(dyc_dx)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    # Upper surface runs from trailing edge to leading edge.
    upper = {
        "x": xu[::-1],
        "y": yu[::-1],
    }
    # Lower surface runs from leading edge back to trailing edge.
    lower = {
        "x": xl[1:],
        "y": yl[1:],
    }

    camber = {
        "x": x,
        "y": yc,
        "dy_dx": dyc_dx,
    }

    return {
        "upper": upper,
        "lower": lower,
        "camber": camber,
    }
