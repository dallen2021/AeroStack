from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .naca import naca4_airfoil


@dataclass(frozen=True)
class AirfoilPreset:
    """Metadata describing a curated airfoil configuration."""

    id: str
    label: str
    family: str
    description: str
    default_alpha: float
    params: Dict[str, str]
    tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        data = {
            "id": self.id,
            "label": self.label,
            "family": self.family,
            "description": self.description,
            "default_alpha": self.default_alpha,
            "params": self.params,
            "tags": list(self.tags),
        }
        digits = self.params.get("digits")
        if self.family == "naca4" and digits:
            data["metrics"] = naca4_metrics(digits)
        return data


def naca4_metrics(digits: str) -> Dict[str, float]:
    """Return simple geometric metrics for a 4-digit NACA identifier."""
    if len(digits) != 4 or not digits.isdigit():
        raise ValueError("NACA 4-digit code must be four digits long")
    m = int(digits[0]) / 100.0
    p = int(digits[1]) / 10.0
    t = int(digits[2:]) / 100.0
    return {
        "max_camber_pct": round(m * 100, 3),
        "max_camber_x_pct": round(p * 10, 3),
        "max_thickness_pct": round(t * 100, 3),
    }


PRESET_AIRFOILS: Tuple[AirfoilPreset, ...] = (
    AirfoilPreset(
        id="naca-0012",
        label="NACA 0012",
        family="naca4",
        description="Symmetric baseline airfoil common in wind-tunnel benchmarks.",
        default_alpha=4.0,
        params={"digits": "0012"},
        tags=("symmetric", "benchmark"),
    ),
    AirfoilPreset(
        id="naca-0018",
        label="NACA 0018",
        family="naca4",
        description="Thick symmetric profile useful for vertical tails and flying wings.",
        default_alpha=4.0,
        params={"digits": "0018"},
        tags=("symmetric", "thick"),
    ),
    AirfoilPreset(
        id="naca-1408",
        label="NACA 1408",
        family="naca4",
        description="Lightly cambered thin section for sailplanes and low-Reynolds applications.",
        default_alpha=3.0,
        params={"digits": "1408"},
        tags=("glider", "low-Re"),
    ),
    AirfoilPreset(
        id="naca-2309",
        label="NACA 2309",
        family="naca4",
        description="Classic mild-camber wing section suited for trainers and UAVs.",
        default_alpha=3.5,
        params={"digits": "2309"},
        tags=("trainer", "balanced"),
    ),
    AirfoilPreset(
        id="naca-2412",
        label="NACA 2412",
        family="naca4",
        description="Popular general aviation airfoil with moderate camber.",
        default_alpha=4.0,
        params={"digits": "2412"},
        tags=("general-aviation", "cambered"),
    ),
    AirfoilPreset(
        id="naca-3415",
        label="NACA 3415",
        family="naca4",
        description="High-camber wing section prioritizing maximum lift at low speeds.",
        default_alpha=2.5,
        params={"digits": "3415"},
        tags=("short-takeoff", "high-lift"),
    ),
    AirfoilPreset(
        id="naca-4412",
        label="NACA 4412",
        family="naca4",
        description="High-camber airfoil suited for low-speed lift-focused designs.",
        default_alpha=2.0,
        params={"digits": "4412"},
        tags=("high-lift", "trainer"),
    ),
    AirfoilPreset(
        id="naca-4415",
        label="NACA 4415",
        family="naca4",
        description="Thicker variant of the 4412 offering extra structural depth.",
        default_alpha=2.0,
        params={"digits": "4415"},
        tags=("high-lift", "thick"),
    ),
    AirfoilPreset(
        id="naca-6312",
        label="NACA 6312",
        family="naca4",
        description="Laminar-friendly section with camber pushed forward for smoother flow.",
        default_alpha=1.5,
        params={"digits": "6312"},
        tags=("laminar", "forward-camber"),
    ),
    AirfoilPreset(
        id="naca-6409",
        label="NACA 6409",
        family="naca4",
        description="Laminar-flow oriented section with forward camber.",
        default_alpha=0.0,
        params={"digits": "6409"},
        tags=("laminar", "forward-camber"),
    ),
    AirfoilPreset(
        id="naca-9306",
        label="NACA 9306",
        family="naca4",
        description="Extreme camber concept showcasing aggressive low-speed performance.",
        default_alpha=0.0,
        params={"digits": "9306"},
        tags=("concept", "experimental"),
    ),
)


_PRESET_LOOKUP: Dict[str, AirfoilPreset] = {preset.id: preset for preset in PRESET_AIRFOILS}


def list_presets() -> List[Dict[str, object]]:
    return [preset.to_dict() for preset in PRESET_AIRFOILS]


def get_preset(preset_id: str) -> AirfoilPreset:
    try:
        return _PRESET_LOOKUP[preset_id]
    except KeyError as exc:
        raise KeyError(f"Unknown airfoil preset '{preset_id}'") from exc


def generate_airfoil(
    family: str,
    chord: float,
    n_points: int,
    **params: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if family == "naca4":
        digits = params.get("digits")
        if not digits:
            raise ValueError("NACA4 airfoils require a 'digits' parameter")
        return naca4_airfoil(digits, chord, n_points)
    raise ValueError(f"Unsupported airfoil family '{family}'")


def generate_preset_airfoil(
    preset_id: str,
    chord: float,
    n_points: int,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    preset = get_preset(preset_id)
    return generate_airfoil(preset.family, chord, n_points, **preset.params)

