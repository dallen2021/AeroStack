from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import numpy as np

from solvers.thin_airfoil import thin_airfoil_CL
from solvers.vortex_panel import vortex_panel_cp
from airfoils.naca import naca4_airfoil

app = FastAPI(title="AeroSnack API", version="1.0")

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


@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest):
    x = np.asarray(req.x)
    yu = np.asarray(req.yu)
    yl = np.asarray(req.yl)

    # Concatenate upper (LE→TE) and lower (TE→LE) to make a closed polygon
    x_sur = np.concatenate([x, x[::-1]])
    y_sur = np.concatenate([yu, yl[::-1]])

    alpha_rad = np.deg2rad(req.alpha_deg)

    # Vortex panel Cp along surface
    s_mid, x_mid, y_mid, cp = vortex_panel_cp(x_sur, y_sur, alpha_rad, V_inf=req.V_inf, N=req.panels)

    # Thin airfoil theory CL
    # Estimate zero-lift alpha from camber built into provided geometry by fitting camber line
    x_camber = x
    camber = 0.5 * (yu + yl)
    cl_tat = thin_airfoil_CL(alpha_rad, x_camber, camber)

    return {
        "alpha_deg": req.alpha_deg,
        "cl_thin_airfoil": cl_tat,
        "surface": {
            "s_mid": s_mid.tolist(),
            "x_mid": x_mid.tolist(),
            "y_mid": y_mid.tolist(),
            "cp": cp.tolist(),
        },
    }
