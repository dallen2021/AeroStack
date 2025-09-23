import numpy as np
from typing import Tuple


def naca4_airfoil(
    digits: str = "2412", chord: float = 1.0, n_points: int = 200
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate NACA 4-digit airfoil coordinates with cosine spacing."""
    if len(digits) != 4 or not digits.isdigit():
        raise ValueError("digits must be a 4-digit string like '2412'")
    m = int(digits[0]) / 100.0
    p = int(digits[1]) / 10.0
    t = int(digits[2:]) / 100.0

    beta = np.linspace(0, np.pi, n_points)
    x = (1 - np.cos(beta)) / 2

    yt = 5 * t * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - 0.1015 * x**4
    )

    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    for i, xi in enumerate(x):
        if p == 0:
            yc[i] = 0.0
            dyc_dx[i] = 0.0
        elif xi < p:
            yc[i] = m / (p**2) * (2 * p * xi - xi**2)
            dyc_dx[i] = 2 * m / (p**2) * (p - xi)
        else:
            yc[i] = m / ((1 - p) ** 2) * ((1 - 2 * p) + 2 * p * xi - xi**2)
            dyc_dx[i] = 2 * m / ((1 - p) ** 2) * (p - xi)

    theta = np.arctan(dyc_dx)
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)

    return x * chord, yu * chord, yl * chord
