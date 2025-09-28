from __future__ import annotations

from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from airfoils.library import (
    generate_preset_airfoil,
    get_preset,
    list_presets,
)
from airfoils.naca import naca4_airfoil
from solvers.thin_airfoil import thin_airfoil_CL
from solvers.vortex_panel import solve_vortex_panel

app = FastAPI(title="AeroStack API", version="1.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AirfoilRequest(BaseModel):
    digits: str = "2412"
    chord: float = 1.0
    n_points: int = 200


class AnalyzeRequest(BaseModel):
    x: List[float]
    yu: List[float]
    yl: List[float]
    alpha_deg: float = 4.0
    V_inf: float = 1.0
    panels: int = 120


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/airfoils")
def api_airfoil_presets():
    return {"presets": list_presets()}


@app.get("/api/airfoils/{preset_id}")
def api_airfoil_preset(
    preset_id: str,
    chord: float = 1.0,
    n_points: int = 200,
):
    try:
        preset = get_preset(preset_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    x, yu, yl = generate_preset_airfoil(preset_id, chord, n_points)
    return {
        "preset": preset.to_dict(),
        "geometry": {
            "chord": chord,
            "n_points": n_points,
            "x": x.tolist(),
            "yu": yu.tolist(),
            "yl": yl.tolist(),
        },
    }


@app.get("/api/naca4")
def api_naca4(digits: str = "2412", chord: float = 1.0, n_points: int = 200):
    x, yu, yl = naca4_airfoil(digits, chord, n_points)
    return {
        "digits": digits,
        "chord": chord,
        "n_points": n_points,
        "x": x.tolist(),
        "yu": yu.tolist(),
        "yl": yl.tolist(),
    }


# Use a dense, solver-only resampling to decouple Cp from UI geometry points
_DENSE_SOLVER_POINTS = 801


def _stitch_closed_surface_no_duplicates(
    x: np.ndarray,
    yu: np.ndarray,
    yl: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a closed airfoil polygon without duplicating LE/TE nodes.

    Upper:  x[0] -> x[-1] (LE to TE)
    Lower:  x[-1] -> x[0] (TE to LE), excluding both endpoints to avoid duplicates.
    """
    if x.ndim != 1:
        x = np.asarray(x).ravel()
        yu = np.asarray(yu).ravel()
        yl = np.asarray(yl).ravel()

    if len(x) < 3:
        raise ValueError("geometry needs at least 3 points")

    x_down = x[-2:0:-1]
    y_down = yl[-2:0:-1]

    x_sur = np.concatenate([x, x_down])
    y_sur = np.concatenate([yu, y_down])
    return x_sur, y_sur


def _prepare_solver_surface(
    x: np.ndarray,
    yu: np.ndarray,
    yl: np.ndarray,
    dense_points: int = _DENSE_SOLVER_POINTS,
) -> tuple[np.ndarray, np.ndarray]:
    """Resample geometry on a fixed dense x-grid then stitch without duplicates."""
    x = np.asarray(x)
    yu = np.asarray(yu)
    yl = np.asarray(yl)

    # Ensure strictly increasing x for interpolation
    order = np.argsort(x)
    x = x[order]
    yu = yu[order]
    yl = yl[order]

    x_dense = np.linspace(float(x[0]), float(x[-1]), int(dense_points))
    yu_dense = np.interp(x_dense, x, yu)
    yl_dense = np.interp(x_dense, x, yl)

    return _stitch_closed_surface_no_duplicates(x_dense, yu_dense, yl_dense)


@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest):
    x = np.asarray(req.x)
    yu = np.asarray(req.yu)
    yl = np.asarray(req.yl)

    # Dense, duplicate-free surface for robust panelization
    x_sur, y_sur = _prepare_solver_surface(x, yu, yl)

    alpha_rad = np.deg2rad(req.alpha_deg)

    solution = solve_vortex_panel(
        x_sur, y_sur, alpha_rad, V_inf=req.V_inf, N=req.panels
    )

    # Use the same dense camber for thin-airfoil CL to keep consistency
    x_camber = np.linspace(float(x[0]), float(x[-1]), _DENSE_SOLVER_POINTS)
    yu_c = np.interp(x_camber, x, yu)
    yl_c = np.interp(x_camber, x, yl)
    camber = 0.5 * (yu_c + yl_c)
    cl_tat = thin_airfoil_CL(alpha_rad, x_camber, camber)

    return {
        "alpha_deg": req.alpha_deg,
        "cl_thin_airfoil": cl_tat,
        "surface": {
            "s_mid": solution.s_mid.tolist(),
            "x_mid": solution.x_mid.tolist(),
            "y_mid": solution.y_mid.tolist(),
            "cp": solution.cp.tolist(),
        },
    }
