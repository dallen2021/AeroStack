# AeroStack

AeroStack is a playground for exploring parametric NACA 4-digit airfoils with thin-airfoil theory and a vortex panel solver. The project ships with a FastAPI backend and a React + Plotly frontend.

## Getting started

### Backend

```bash
cd server
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

By default the frontend connects to `http://127.0.0.1:8000` for API calls. Override this by setting `VITE_API_BASE` before running the dev server.

## Features

- Cosine-spaced NACA 4-digit generator (geometry + camber line).
- Thin-airfoil solver returning zero-lift angle and lift slope.
- Constant-strength vortex panel solver (≤100 panels) for Cp distribution and circulation-derived lift.
- Metrics for solver time, vortex vs. thin-airfoil lift error, and solver memory footprint.
- DXF export for rib geometry with configurable chord and thickness scale.

Future extensions include XFoil integration, caching of high-fidelity runs, and gradient-based optimization for bespoke target lift curves.
