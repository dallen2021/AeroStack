# AeroSnack (FastAPI + React)

A fast, truthful-enough airfoil explorer:
- Generate NACA 4-digit airfoils with cosine spacing
- Thin-airfoil CL with zero-lift angle estimated from camber line
- Constant-strength vortex panel Cp with Kutta condition

## Dev quickstart

### Backend
```bash
cd server
python -m venv .venv && source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd web
npm i
npm run dev
```
Open http://localhost:5173 and ensure API points to http://127.0.0.1:8000 (default).

## Notes
- Cp uses a simplified vortex-panel kernel; for sharp trailing edges it enforces a single Kutta equation between the last and first panels. For serious use, upgrade to a doublet/source formulation or a higher-order vortex panel with explicit TE control points.
- Thin-airfoil integration maps a \(\theta\)-grid to chordwise x for a stable zero-lift estimate.
- Geometry endpoint returns monotone x with separate upper/lower y for robust plotting.

## Roadmap
- Export DXF of ribs, STL stack
- Add XFoil subprocess baseline + caching
- Optimization: match target Cl@alpha with gradient on (m,p,t)
