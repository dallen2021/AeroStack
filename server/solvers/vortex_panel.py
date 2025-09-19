"""Vortex panel implementation for Cp distribution."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class PanelResult:
    cp_x: List[float]
    cp: List[float]
    gamma: List[float]
    cl: float


def _build_closed_surface(
    upper: Tuple[np.ndarray, np.ndarray],
    lower: Tuple[np.ndarray, np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    xu, yu = upper
    xl, yl = lower
    if not (np.isclose(xl[-1], xu[0]) and np.isclose(yl[-1], yu[0])):
        xl = np.concatenate([xl, [xu[0]]])
        yl = np.concatenate([yl, [yu[0]]])
    x = np.concatenate([xu, xl[1:]])
    y = np.concatenate([yu, yl[1:]])
    if not (np.isclose(x[0], x[-1]) and np.isclose(y[0], y[-1])):
        x = np.concatenate([x, [x[0]]])
        y = np.concatenate([y, [y[0]]])
    return x, y


def _panel_geometry(
    x: np.ndarray, y: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    dx = x[1:] - x[:-1]
    dy = y[1:] - y[:-1]
    length = np.hypot(dx, dy)
    beta = np.arctan2(dy, dx)
    tx = np.cos(beta)
    ty = np.sin(beta)
    nx = ty
    ny = -tx
    xc = 0.5 * (x[:-1] + x[1:])
    yc = 0.5 * (y[:-1] + y[1:])
    return (
        length,
        beta,
        np.column_stack((tx, ty)),
        np.column_stack((nx, ny)),
        np.column_stack((xc, yc)),
    )


def _point_vortex_velocity(px: float, py: float, x: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    rx = px - x
    ry = py - y
    r2 = rx**2 + ry**2
    with np.errstate(divide="ignore", invalid="ignore"):
        u = -(1.0 / (2 * math.pi)) * np.where(r2 > 0, ry / r2, 0.0)
        v = (1.0 / (2 * math.pi)) * np.where(r2 > 0, rx / r2, 0.0)
    return u, v


def solve_vortex_panel(
    upper: Tuple[np.ndarray, np.ndarray],
    lower: Tuple[np.ndarray, np.ndarray],
    alpha_deg: float,
    panel_subdivisions: int = 3,
) -> PanelResult:
    x, y = _build_closed_surface(upper, lower)
    length, beta, tangents, normals, control_points = _panel_geometry(x, y)
    n_panels = len(length)

    alpha_rad = math.radians(alpha_deg)
    v_inf = np.array([math.cos(alpha_rad), math.sin(alpha_rad)])

    # Build influence matrix using point-vortex quadrature.
    A = np.zeros((n_panels + 1, n_panels))
    b = np.zeros(n_panels + 1)

    subdivision = max(1, panel_subdivisions)
    for j in range(n_panels):
        x_start, y_start = x[j], y[j]
        x_end, y_end = x[j + 1], y[j + 1]
        segment = np.linspace(0.0, 1.0, subdivision, endpoint=False) + 1.0 / (subdivision + 1)
        px = x_start + (x_end - x_start) * segment
        py = y_start + (y_end - y_start) * segment

        u, v = _point_vortex_velocity(control_points[:, 0][:, None], control_points[:, 1][:, None], px, py)
        v_normal = u * normals[:, 0][:, None] + v * normals[:, 1][:, None]
        v_tangent = u * tangents[:, 0][:, None] + v * tangents[:, 1][:, None]
        influence = length[j] / subdivision * v_normal
        influence_t = length[j] / subdivision * v_tangent
        A[:n_panels, j] = influence.sum(axis=1)
        A[n_panels, j] = influence_t[0].sum() + influence_t[-1].sum()

    # Right-hand side enforces flow tangency.
    b[:n_panels] = -normals[:, 0] * v_inf[0] - normals[:, 1] * v_inf[1]
    # Kutta condition: tangential velocities at the trailing edge panels match.
    b[n_panels] = -(tangents[0, 0] * v_inf[0] + tangents[0, 1] * v_inf[1]) - (
        tangents[-1, 0] * v_inf[0] + tangents[-1, 1] * v_inf[1]
    )

    gamma = np.linalg.lstsq(A, b, rcond=None)[0]

    # Compute tangential velocity and Cp.
    vt = np.zeros(n_panels)
    for j in range(n_panels):
        x_start, y_start = x[j], y[j]
        x_end, y_end = x[j + 1], y[j + 1]
        segment = np.linspace(0.0, 1.0, subdivision, endpoint=False) + 1.0 / (subdivision + 1)
        px = x_start + (x_end - x_start) * segment
        py = y_start + (y_end - y_start) * segment
        u, v = _point_vortex_velocity(control_points[:, 0][:, None], control_points[:, 1][:, None], px, py)
        v_tangent = u * tangents[:, 0][:, None] + v * tangents[:, 1][:, None]
        vt += gamma[j] * length[j] / subdivision * v_tangent.sum(axis=1)

    vt += tangents[:, 0] * v_inf[0] + tangents[:, 1] * v_inf[1]
    cp = 1.0 - vt**2

    gamma_total = np.sum(gamma * length)
    cl = 2 * gamma_total

    return PanelResult(
        cp_x=list(control_points[:, 0]),
        cp=list(cp.astype(float)),
        gamma=list(gamma.astype(float)),
        cl=float(cl),
    )
