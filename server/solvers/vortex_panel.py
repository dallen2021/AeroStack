import numpy as np


def _build_panels(x: np.ndarray, y: np.ndarray, N: int):
    s = np.concatenate([[0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    S = s[-1]
    s_uniform = np.linspace(0, S, N + 1)
    x_u = np.interp(s_uniform, s, x)
    y_u = np.interp(s_uniform, s, y)

    x_mid = 0.5 * (x_u[:-1] + x_u[1:])
    y_mid = 0.5 * (y_u[:-1] + y_u[1:])
    dx = x_u[1:] - x_u[:-1]
    dy = y_u[1:] - y_u[:-1]
    length = np.hypot(dx, dy)

    tx = dx / length
    ty = dy / length
    nx = -ty
    ny = tx

    return x_u, y_u, x_mid, y_mid, tx, ty, nx, ny, length, s_uniform


def vortex_panel_cp(
    x: np.ndarray,
    y: np.ndarray,
    alpha: float,
    V_inf: float = 1.0,
    N: int = 160,
):
    """Compute Cp distribution using constant-strength vortex panels."""
    area = 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))
    if area < 0:
        x = x[::-1]
        y = y[::-1]

    x_u, y_u, x_mid, y_mid, tx, ty, nx, ny, L, s = _build_panels(x, y, N)

    A = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            dxj = x_mid[i] - x_u[j]
            dyj = y_mid[i] - y_u[j]
            cos_t = (x_u[j + 1] - x_u[j]) / L[j]
            sin_t = (y_u[j + 1] - y_u[j]) / L[j]
            xloc1 = dxj * cos_t + dyj * sin_t
            yloc1 = -dxj * sin_t + dyj * cos_t
            xloc2 = xloc1 - L[j]
            yloc2 = yloc1

            def phi(xl, yl):
                return np.arctan2(yl * L[j], xl * xl + yl * yl - xl * L[j])

            def psi(xl, yl):
                r1 = np.hypot(xl, yl)
                r2 = np.hypot(xl - L[j], yl)
                return 0.5 * np.log((r1 * r1) / (r2 * r2 + 1e-30))

            u_tan_local = (phi(xloc1, yloc1) - phi(xloc2, yloc2)) / (2 * np.pi)
            v_norm_local = (psi(xloc1, yloc1) - psi(xloc2, yloc2)) / (2 * np.pi)
            ui = u_tan_local * cos_t - v_norm_local * sin_t
            vi = u_tan_local * sin_t + v_norm_local * cos_t
            A[i, j] = ui * tx[i] + vi * ty[i]

    U_inf = V_inf * np.cos(alpha)
    V_inf_y = V_inf * np.sin(alpha)
    U_tan_inf = U_inf * tx + V_inf_y * ty

    b = -U_tan_inf.copy()
    A_aug = A.copy()
    b_aug = b.copy()
    A_te = A[0, :] - A[-1, :]
    kutta_rhs = -(U_tan_inf[0] - U_tan_inf[-1])
    A_aug[-1, :] = A_te
    b_aug[-1] = kutta_rhs

    gamma = np.linalg.lstsq(A_aug, b_aug, rcond=None)[0]

    V_tan = U_tan_inf + A @ gamma
    Cp = 1.0 - (V_tan / V_inf) ** 2

    s_mid = 0.5 * (s[:-1] + s[1:])
    return s_mid, x_mid, y_mid, Cp
