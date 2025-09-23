import numpy as np


def zero_lift_alpha(x: np.ndarray, zc: np.ndarray) -> float:
    """Compute zero-lift angle (radians) from camber line via thin-airfoil integral.

    Parameters
    ----------
    x : array_like
        Chordwise coordinates on [0, 1].
    zc : array_like
        Camber line coordinates corresponding to ``x``.

    Returns
    -------
    float
        Zero-lift angle of attack (radians).
    """
    dzdx = np.gradient(zc, x, edge_order=2)
    theta = np.linspace(1e-6, np.pi - 1e-6, 1000)
    x_theta = 0.5 * (1 - np.cos(theta))
    dzdx_theta = np.interp(x_theta, x, dzdx)
    integrand = dzdx_theta * (1 - np.cos(theta)) / np.sin(theta)
    alpha0 = -(1 / np.pi) * np.trapz(integrand, theta)
    return float(alpha0)


def thin_airfoil_CL(alpha: float, x: np.ndarray, zc: np.ndarray) -> float:
    """Return thin-airfoil lift coefficient for geometry-defined camber line."""
    alpha0 = zero_lift_alpha(x, zc)
    cl = 2 * np.pi * (alpha - alpha0)
    return float(cl)
