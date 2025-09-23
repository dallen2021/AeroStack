import numpy as np


# Thin airfoil theory:
#   CL = 2*pi*(alpha - alpha0)
# where alpha0 = - (1/pi) * integral_0^pi (dz_dx(theta) * (1 - cos theta)/sin theta dtheta)
# We approximate dz/dx from camber line samples; map theta->x = (1-cos theta)/2 on unit chord.

def zero_lift_alpha(x: np.ndarray, zc: np.ndarray) -> float:
    """Compute zero-lift angle (radians) from camber line via thin-airfoil integral.
    x, zc on [0,1]. Returns alpha0 (radians)."""
    # Estimate dz/dx with central differences
    dzdx = np.gradient(zc, x, edge_order=2)
    # Map to theta grid
    theta = np.linspace(1e-6, np.pi - 1e-6, 1000)
    x_theta = 0.5 * (1 - np.cos(theta))
    dzdx_theta = np.interp(x_theta, x, dzdx)
    integrand = dzdx_theta * (1 - np.cos(theta)) / np.sin(theta)
    alpha0 = -(1 / np.pi) * np.trapz(integrand, theta)
    return float(alpha0)


def thin_airfoil_CL(alpha: float, x: np.ndarray, zc: np.ndarray) -> float:
    alpha0 = zero_lift_alpha(x, zc)
    cl = 2 * np.pi * (alpha - alpha0)
    return float(cl)
