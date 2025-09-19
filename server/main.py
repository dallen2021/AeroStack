from __future__ import annotations

import io
import math
import time
from typing import Dict, List

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from .airfoils.naca import InvalidNACACode, naca4_coordinates
from .solvers.thin_airfoil import ThinAirfoilResult, solve_thin_airfoil
from .solvers.vortex_panel import PanelResult, solve_vortex_panel


DEFAULT_ALPHA_RANGE = [-10, -6, -2, 0, 2, 4, 8, 12]
BASELINE_ALPHAS = [-4.0, 0.0, 4.0, 8.0]


class AnalysisRequest(BaseModel):
    naca_code: str = Field(..., regex=r"^\d{4}$")
    alpha_deg: float = 0.0
    panel_count: int = Field(80, ge=20, le=100)
    chord: float = Field(1.0, gt=0.0)
    thickness_scale: float = Field(1.0, gt=0.1)
    alpha_curve: List[float] | None = None

    @field_validator("alpha_curve", mode="before")
    @classmethod
    def _default_alpha_curve(cls, value: List[float] | None) -> List[float]:
        return list(DEFAULT_ALPHA_RANGE) if value is None else list(value)


def _geometry_for_panels(code: str, panel_count: int) -> Dict[str, np.ndarray]:
    points = panel_count // 2 + 1
    geom = naca4_coordinates(code, points_per_surface=points)
    return {
        "upper": (
            np.asarray(geom["upper"]["x"], dtype=float),
            np.asarray(geom["upper"]["y"], dtype=float),
        ),
        "lower": (
            np.asarray(geom["lower"]["x"], dtype=float),
            np.asarray(geom["lower"]["y"], dtype=float),
        ),
        "camber": geom["camber"],
    }


def _baseline_error(
    code: str,
    panel_count: int,
    thin: ThinAirfoilResult,
) -> float:
    geom = _geometry_for_panels(code, panel_count)
    errors: List[float] = []
    for alpha in BASELINE_ALPHAS:
        panel = solve_vortex_panel(geom["upper"], geom["lower"], alpha)
        thin_cl = 2 * math.pi * (math.radians(alpha) - math.radians(thin.alpha_l0_deg))
        errors.append(panel.cl - thin_cl)
    if not errors:
        return 0.0
    return float(math.sqrt(sum(e**2 for e in errors) / len(errors)))


def _estimate_memory_bytes(panel: PanelResult) -> int:
    arrays = [
        np.asarray(panel.cp_x, dtype=float),
        np.asarray(panel.cp, dtype=float),
        np.asarray(panel.gamma, dtype=float),
    ]
    return int(sum(arr.nbytes for arr in arrays))


def _dxf_from_coordinates(
    upper: np.ndarray,
    lower: np.ndarray,
    chord: float,
    thickness_scale: float,
) -> str:
    coords = np.concatenate(
        [
            np.column_stack((upper[:, 0] * chord, upper[:, 1] * chord * thickness_scale)),
            np.column_stack((lower[:, 0] * chord, lower[:, 1] * chord * thickness_scale))[1:-1],
        ]
    )
    coords = np.vstack([coords, coords[0]])
    header = ["0", "SECTION", "2", "ENTITIES", "0", "LWPOLYLINE", "8", "RIB", "90", str(len(coords)), "70", "1"]
    body: List[str] = []
    for x, y in coords:
        body.extend(["10", f"{x:.6f}", "20", f"{y:.6f}"])
    footer = ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(header + body + footer)


app = FastAPI(title="AeroStack API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analysis")
def run_analysis(request: AnalysisRequest) -> JSONResponse:
    try:
        geom = _geometry_for_panels(request.naca_code, request.panel_count)
    except InvalidNACACode as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    start = time.perf_counter()
    thin = solve_thin_airfoil(
        alpha_deg=request.alpha_deg,
        camber_x=np.asarray(geom["camber"]["x"], dtype=float),
        camber_dy_dx=np.asarray(geom["camber"]["dy_dx"], dtype=float),
        alpha_curve_deg=request.alpha_curve,
    )
    panel = solve_vortex_panel(geom["upper"], geom["lower"], request.alpha_deg)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    baseline_error = _baseline_error(request.naca_code, request.panel_count, thin)

    memory_bytes = _estimate_memory_bytes(panel)

    response = {
        "airfoil": {
            "upper": {
                "x": geom["upper"][0].tolist(),
                "y": geom["upper"][1].tolist(),
            },
            "lower": {
                "x": geom["lower"][0].tolist(),
                "y": geom["lower"][1].tolist(),
            },
            "camber": {
                "x": geom["camber"]["x"].tolist(),
                "y": geom["camber"]["y"].tolist(),
            },
        },
        "thin_airfoil": {
            "alpha_l0_deg": thin.alpha_l0_deg,
            "cl": thin.cl,
            "alpha_range": thin.alpha_range_deg,
            "cl_curve": thin.cl_curve,
        },
        "vortex_panel": {
            "cp_x": panel.cp_x,
            "cp": panel.cp,
            "cl": panel.cl,
        },
        "metrics": {
            "solver_time_ms": elapsed_ms,
            "cl_error_baseline": baseline_error,
            "memory_bytes": memory_bytes,
            "panel_count": request.panel_count,
        },
    }

    return JSONResponse(response)


@app.get("/api/export/dxf")
def export_dxf(
    naca_code: str = Query(..., regex=r"^\d{4}$"),
    chord: float = Query(1.0, gt=0.0),
    thickness_scale: float = Query(1.0, gt=0.1),
    panel_count: int = Query(80, ge=20, le=200),
) -> StreamingResponse:
    geom = _geometry_for_panels(naca_code, panel_count)
    upper = np.column_stack((geom["upper"][0], geom["upper"][1]))
    lower = np.column_stack((geom["lower"][0], geom["lower"][1]))
    dxf = _dxf_from_coordinates(upper, lower, chord, thickness_scale)
    buffer = io.BytesIO(dxf.encode("utf-8"))
    filename = f"NACA{naca_code}_chord{chord:.2f}.dxf"
    return StreamingResponse(
        buffer,
        media_type="application/dxf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
