from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


def _build_panels(x: np.ndarray, y: np.ndarray, N: int):
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    S = s[-1]
    s_uniform = np.linspace(0.0, S, N + 1)
    x_nodes = np.interp(s_uniform, s, x)
    y_nodes = np.interp(s_uniform, s, y)

    x_mid = 0.5 * (x_nodes[:-1] + x_nodes[1:])
    y_mid = 0.5 * (y_nodes[:-1] + y_nodes[1:])
    dx = x_nodes[1:] - x_nodes[:-1]
    dy = y_nodes[1:] - y_nodes[:-1]
    length = np.hypot(dx, dy)

    tx = dx / length
    ty = dy / length
    nx = -ty
    ny = tx

    return x_nodes, y_nodes, x_mid, y_mid, tx, ty, nx, ny, length, s_uniform


@dataclass(frozen=True)
class VortexPanelSolution:
    s_mid: np.ndarray
    x_mid: np.ndarray
    y_mid: np.ndarray
    cp: np.ndarray
    gamma: np.ndarray
    panel_length: np.ndarray
    alpha: float
    V_inf: float

    def as_response(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        return self.s_mid, self.x_mid, self.y_mid, self.cp


def solve_vortex_panel(
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
    V_inf: float = 1.0,
    N: int = 160,
) -> VortexPanelSolution:
    """Solve a constant-strength vortex panel system and return full solution."""
    area = 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))
    if area < 0.0:
        x = x[::-1]
        y = y[::-1]

    x_nodes, y_nodes, x_mid, y_mid, tx, ty, nx, ny, length, s = _build_panels(x, y, N)

    A = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            dxj = x_mid[i] - x_nodes[j]
            dyj = y_mid[i] - y_nodes[j]
            cos_t = (x_nodes[j + 1] - x_nodes[j]) / length[j]
            sin_t = (y_nodes[j + 1] - y_nodes[j]) / length[j]
            xloc1 = dxj * cos_t + dyj * sin_t
            yloc1 = -dxj * sin_t + dyj * cos_t
            xloc2 = xloc1 - length[j]
            yloc2 = yloc1

            def phi(xl: float, yl: float) -> float:
                return np.arctan2(yl * length[j], xl * xl + yl * yl - xl * length[j])

            def psi(xl: float, yl: float) -> float:
                r1 = np.hypot(xl, yl)
                r2 = np.hypot(xl - length[j], yl)
                return 0.5 * np.log((r1 * r1) / (r2 * r2 + 1e-30))

            u_tan_local = (phi(xloc1, yloc1) - phi(xloc2, yloc2)) / (2.0 * np.pi)
            v_norm_local = (psi(xloc1, yloc1) - psi(xloc2, yloc2)) / (2.0 * np.pi)
            ui = u_tan_local * cos_t - v_norm_local * sin_t
            vi = u_tan_local * sin_t + v_norm_local * cos_t
            A[i, j] = ui * tx[i] + vi * ty[i]

    U_inf = V_inf * np.cos(alpha)
    V_inf_y = V_inf * np.sin(alpha)
    U_tan_inf = U_inf * tx + V_inf_y * ty

    b = -U_tan_inf.copy()
    A_aug = A.copy()
    b_aug = b.copy()

    # Enforce Kutta condition at the trailing edge: match tangential velocity
    # on the panels immediately adjacent to the TE node.
    k_te = int(np.argmax(x_nodes))  # index of trailing-edge node among N+1 nodes
    i_upper = (k_te - 1) % N        # panel approaching TE along upper surface
    i_lower = (k_te) % N            # panel leaving TE along lower surface

    A_aug[-1, :] = A[i_upper, :] - A[i_lower, :]
    b_aug[-1] = -(U_tan_inf[i_upper] - U_tan_inf[i_lower])

    gamma = np.linalg.lstsq(A_aug, b_aug, rcond=None)[0]

    V_tan = U_tan_inf + A @ gamma
    Cp = 1.0 - (V_tan / V_inf) ** 2

    s_mid = 0.5 * (s[:-1] + s[1:])
    return VortexPanelSolution(
        s_mid=s_mid,
        x_mid=x_mid,
        y_mid=y_mid,
        cp=Cp,
        gamma=gamma,
        panel_length=length,
        alpha=alpha,
        V_inf=V_inf,
    )


def vortex_panel_cp(
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
    V_inf: float = 1.0,
    N: int = 160,
):
    solution = solve_vortex_panel(x, y, alpha, V_inf=V_inf, N=N)
    return solution.as_response()


