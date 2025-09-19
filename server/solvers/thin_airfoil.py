"""Thin-airfoil solver utilities."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List

import numpy as np


@dataclass
class ThinAirfoilResult:
    alpha_l0_deg: float
    cl: float
    alpha_range_deg: List[float]
    cl_curve: List[float]


def _ensure_monotonic(values: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    if arr.ndim != 1:
        raise ValueError("Input must be one-dimensional")
    if not np.all(np.diff(arr) >= 0):
        raise ValueError("Angles must be sorted in ascending order")
    return arr


def solve_thin_airfoil(
    alpha_deg: float,
    camber_x: np.ndarray,
    camber_dy_dx: np.ndarray,
    alpha_curve_deg: Iterable[float] | None = None,
) -> ThinAirfoilResult:
    """Compute the thin-airfoil lift slope and zero-lift angle."""
    if alpha_curve_deg is None:
        alpha_curve_deg = np.linspace(-10.0, 15.0, 30)
    alpha_curve = _ensure_monotonic(alpha_curve_deg)

    theta = np.arccos(1 - 2 * camber_x)
    integrand = camber_dy_dx * np.cos(theta)
    alpha_l0 = -np.trapz(integrand, theta) / math.pi

    alpha_rad = math.radians(alpha_deg)
    cl = 2 * math.pi * (alpha_rad - alpha_l0)

    cl_curve = 2 * math.pi * (np.radians(alpha_curve) - alpha_l0)

    return ThinAirfoilResult(
        alpha_l0_deg=math.degrees(alpha_l0),
        cl=float(cl),
        alpha_range_deg=list(alpha_curve.astype(float)),
        cl_curve=list(cl_curve.astype(float)),
    )
