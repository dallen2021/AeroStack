import React, { useCallback, useEffect, useMemo, useState } from 'react'
import Plotly from 'plotly.js-dist-min'

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

type PlotProps = {
  data: Plotly.Data[]
  layout: Partial<Plotly.Layout>
}

function Plot({ data, layout }: PlotProps) {
  const ref = React.useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    Plotly.newPlot(ref.current, data, { ...layout, responsive: true })
    const onResize = () => Plotly.Plots.resize(ref.current!)
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      Plotly.purge(ref.current!)
    }
  }, [data, layout])
  return <div ref={ref} />
}

type Airfoil = { x: number[]; yu: number[]; yl: number[] }

type Analysis = {
  alpha_deg: number
  cl_thin_airfoil: number
  surface: { s_mid: number[]; x_mid: number[]; y_mid: number[]; cp: number[] }
}

export default function App() {
  const [digits, setDigits] = useState('2412')
  const [alpha, setAlpha] = useState(4)
  const [nPoints, setNPoints] = useState(200)
  const [panels, setPanels] = useState(120)
  const [airfoil, setAirfoil] = useState<Airfoil | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchAirfoil = useCallback(async () => {
    const res = await fetch(
      `${API}/api/naca4?digits=${digits}&chord=1&n_points=${nPoints}`
    )
    const json = await res.json()
    setAirfoil({ x: json.x, yu: json.yu, yl: json.yl })
  }, [digits, nPoints])

  const runAnalysis = useCallback(async () => {
    if (!airfoil) return
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x: airfoil.x,
          yu: airfoil.yu,
          yl: airfoil.yl,
          alpha_deg: alpha,
          V_inf: 1.0,
          panels,
        }),
      })
      const json = await res.json()
      setAnalysis(json)
    } finally {
      setLoading(false)
    }
  }, [airfoil, alpha, panels])

  useEffect(() => {
    fetchAirfoil()
  }, [fetchAirfoil])

  useEffect(() => {
    runAnalysis()
  }, [runAnalysis])

  const airfoilPlot = useMemo(() => {
    if (!airfoil) return null
    return {
      data: [
        { x: airfoil.x, y: airfoil.yu, mode: 'lines', name: 'Upper' },
        { x: airfoil.x, y: airfoil.yl, mode: 'lines', name: 'Lower' },
      ],
      layout: {
        title: `NACA ${digits} geometry`,
        xaxis: { title: 'x/c', range: [0, 1] },
        yaxis: { title: 'y/c', scaleanchor: 'x' },
        margin: { t: 40 },
      },
    }
  }, [airfoil, digits])

  const cpPlot = useMemo(() => {
    if (!analysis) return null
    const s = analysis.surface.s_mid
    const cp = analysis.surface.cp
    return {
      data: [{ x: s, y: cp, mode: 'lines+markers', name: 'Cp' }],
      layout: {
        title: `Cp distribution @ α=${alpha.toFixed(2)}°`,
        xaxis: { title: 's (arc length)' },
        yaxis: { title: 'Cp', autorange: 'reversed' },
        margin: { t: 40 },
      },
    }
  }, [analysis, alpha])

  return (
    <div className="grid">
      <div className="panel">
        <h2>AeroSnack</h2>
        <p>Parametric airfoil explorer with thin-airfoil & vortex panel analysis.</p>

        <label>NACA 4-digit</label>
        <input
          value={digits}
          onChange={(e) => setDigits(e.target.value.replace(/[^0-9]/g, '').slice(0, 4))}
        />

        <div className="row">
          <div>
            <label>α (deg)</label>
            <input
              type="number"
              value={alpha}
              step={0.5}
              onChange={(e) => setAlpha(parseFloat(e.target.value))}
            />
          </div>
          <div>
            <label>Points (geometry)</label>
            <input
              type="number"
              value={nPoints}
              min={50}
              max={600}
              onChange={(e) => setNPoints(parseInt(e.target.value || '200'))}
            />
          </div>
        </div>
        <div className="row">
          <div>
            <label>Panels (solver)</label>
            <input
              type="number"
              value={panels}
              min={40}
              max={300}
              onChange={(e) => setPanels(parseInt(e.target.value || '120'))}
            />
          </div>
          <div>
            <label>CL (thin-airfoil)</label>
            <input value={analysis?.cl_thin_airfoil?.toFixed(3) ?? ''} readOnly />
          </div>
        </div>

        <div style={{ marginTop: 12 }}>
          <button onClick={fetchAirfoil}>Regenerate airfoil</button>
          <button onClick={runAnalysis} style={{ marginLeft: 8 }} disabled={loading}>
            {loading ? 'Analyzing…' : 'Re-run analysis'}
          </button>
        </div>

        <div className="legend">
          Cp plot uses a simple constant-strength vortex panel method with a Kutta condition.
          Thin-airfoil CL uses a zero-lift α estimated from the camber line.
        </div>
        <div className="footer">API: {API}</div>
      </div>
      <div className="plot">
        {airfoilPlot && <Plot data={airfoilPlot.data} layout={airfoilPlot.layout} />}
        {cpPlot && (
          <div style={{ marginTop: 16 }}>
            <Plot data={cpPlot.data} layout={cpPlot.layout} />
          </div>
        )}
      </div>
    </div>
  )
}
