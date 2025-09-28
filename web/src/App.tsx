import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import Plotly from 'plotly.js-dist-min'
import './App.css'

const API = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

type PlotProps = {
  data: Plotly.Data[]
  layout: Partial<Plotly.Layout>
  className?: string
  style?: React.CSSProperties
}

function Plot({ data, layout, className, style }: PlotProps) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const plotLayout: Partial<Plotly.Layout> = {
      autosize: true,
      ...layout,
    }
    const config: Partial<Plotly.Config> = {
      responsive: true,
      displaylogo: false,
    }
    Plotly.react(ref.current, data, plotLayout, config)
    const handleResize = () => {
      if (ref.current) Plotly.Plots.resize(ref.current)
    }
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      if (ref.current) Plotly.purge(ref.current)
    }
  }, [data, layout])
  return (
    <div
      ref={ref}
      className={className}
      style={{ width: '100%', ...(style ?? {}) }}
    />
  )
}

type Airfoil = { x: number[]; yu: number[]; yl: number[] }

type Analysis = {
  alpha_deg: number
  cl_thin_airfoil: number
  surface: { s_mid: number[]; x_mid: number[]; y_mid: number[]; cp: number[] }
}

type AirfoilPreset = {
  id: string
  label: string
  family: string
  description: string
  default_alpha: number
  params: { digits?: string }
  tags: string[]
  metrics?: {
    max_camber_pct: number
    max_camber_x_pct: number
    max_thickness_pct: number
  }
}

const formatNumber = (value: number | null | undefined, digits = 3) => {
  if (value == null || Number.isNaN(value)) return 'N/A'
  return value.toFixed(digits)
}

export default function App() {
  const [presets, setPresets] = useState<AirfoilPreset[]>([])
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)
  const [digits, setDigits] = useState('2412')
  const [alpha, setAlpha] = useState(4)
  const [nPoints, setNPoints] = useState(200)
  const [panels, setPanels] = useState(120)
  const [airfoil, setAirfoil] = useState<Airfoil | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const initialisedPresets = useRef(false)

  useEffect(() => {
    let cancelled = false
    const loadPresets = async () => {
      try {
        const res = await fetch(`${API}/api/airfoils`)
        if (!res.ok) throw new Error('Failed to load preset airfoils')
        const json = await res.json()
        if (!cancelled) setPresets(json.presets ?? [])
      } catch (err) {
        console.error(err)
        if (!cancelled) setError((err as Error).message)
      }
    }
    loadPresets()
    return () => {
      cancelled = true
    }
  }, [])

  const fetchPresetGeometry = useCallback(
    async (presetId: string, opts: { syncAlpha?: boolean } = {}) => {
      setError(null)
      const params = new URLSearchParams({ chord: '1', n_points: String(nPoints) })
      const res = await fetch(`${API}/api/airfoils/${presetId}?${params.toString()}`)
      if (!res.ok) throw new Error('Failed to load preset geometry')
      const json = await res.json()
      const preset: AirfoilPreset = json.preset
      const geometry = json.geometry
      if (opts.syncAlpha !== false) setAlpha(preset.default_alpha)
      setDigits(preset.params?.digits ?? '0000')
      setAirfoil({ x: geometry.x, yu: geometry.yu, yl: geometry.yl })
      setSelectedPreset(presetId)
    },
    [nPoints],
  )

  const fetchCustomAirfoil = useCallback(async () => {
    setError(null)
    if (digits.length !== 4) {
      setAirfoil(null)
      return
    }
    const params = new URLSearchParams({
      digits,
      chord: '1',
      n_points: String(nPoints),
    })
    const res = await fetch(`${API}/api/naca4?${params.toString()}`)
    if (!res.ok) throw new Error('Unable to generate NACA geometry')
    const json = await res.json()
    setAirfoil({ x: json.x, yu: json.yu, yl: json.yl })
  }, [digits, nPoints])

  const computeAnalysis = useCallback(
    async (airfoilShape: Airfoil) => {
      setAnalysisLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API}/api/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            x: airfoilShape.x,
            yu: airfoilShape.yu,
            yl: airfoilShape.yl,
            alpha_deg: alpha,
            V_inf: 1.0,
            panels,
          }),
        })
        if (!res.ok) throw new Error('Analysis failed')
        const json = await res.json()
        setAnalysis(json)
      } catch (err) {
        console.error(err)
        setError((err as Error).message)
      } finally {
        setAnalysisLoading(false)
      }
    },
    [alpha, panels],
  )

  useEffect(() => {
    if (!presets.length || initialisedPresets.current) return
    const preferred = presets.find((preset) => preset.params?.digits === digits)
    const target = preferred ?? presets[0]
    initialisedPresets.current = true
    fetchPresetGeometry(target.id).catch((err) => setError((err as Error).message))
  }, [digits, fetchPresetGeometry, presets])

  useEffect(() => {
    if (!airfoil) return
    computeAnalysis(airfoil)
  }, [airfoil, alpha, panels, computeAnalysis])

  useEffect(() => {
    if (!selectedPreset || selectedPreset === 'custom') return
    fetchPresetGeometry(selectedPreset, { syncAlpha: false }).catch((err) =>
      setError((err as Error).message),
    )
  }, [fetchPresetGeometry, nPoints, selectedPreset])

  useEffect(() => {
    if (selectedPreset !== 'custom') return
    const handle = window.setTimeout(() => {
      fetchCustomAirfoil().catch((err) => setError((err as Error).message))
    }, 250)
    return () => window.clearTimeout(handle)
  }, [digits, fetchCustomAirfoil, selectedPreset])

  useEffect(() => {
    if (selectedPreset !== 'custom') return
    fetchCustomAirfoil().catch((err) => setError((err as Error).message))
  }, [fetchCustomAirfoil, nPoints, selectedPreset])

  const airfoilPlot = useMemo(() => {
    if (!airfoil) return null
    const fillX = [...airfoil.x, ...airfoil.x.slice().reverse()]
    const fillY = [...airfoil.yu, ...airfoil.yl.slice().reverse()]
    return {
      data: [
        {
          x: airfoil.x,
          y: airfoil.yu,
          mode: 'lines',
          name: 'Upper surface',
          line: { color: '#5ac8fa', width: 2 },
        },
        {
          x: airfoil.x,
          y: airfoil.yl,
          mode: 'lines',
          name: 'Lower surface',
          line: { color: '#80d46b', width: 2 },
        },
        {
          x: fillX,
          y: fillY,
          fill: 'toself',
          mode: 'lines',
          line: { width: 0 },
          fillcolor: 'rgba(90, 200, 250, 0.08)',
          hoverinfo: 'skip',
          showlegend: false,
        },
      ],
      layout: {
        title: `Airfoil geometry (${selectedPreset ?? 'custom'})`,
        xaxis: { title: 'x/c', range: [-0.2, 1.2] },
        yaxis: { title: 'y/c', scaleanchor: 'x', range: [-0.6, 0.6] },
        margin: { t: 50, r: 20, b: 50, l: 60 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        legend: { orientation: 'h', x: 0, y: 1.1 },
      } as Partial<Plotly.Layout>,
    }
  }, [airfoil, selectedPreset])

  const cpPlot = useMemo(() => {
    if (!analysis) return null
    return {
      data: [
        {
          x: analysis.surface.s_mid,
          y: analysis.surface.cp,
          mode: 'lines+markers',
          line: { color: '#f5a623', width: 2 },
          marker: { size: 4 },
          name: 'Cp',
        },
      ],
      layout: {
        title: `Surface Cp @ alpha = ${alpha.toFixed(2)} deg`,
        xaxis: { title: 'Arc length (s)' },
        yaxis: { title: 'Cp', autorange: 'reversed' },
        margin: { t: 50, r: 20, b: 50, l: 60 },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
      } as Partial<Plotly.Layout>,
    }
  }, [analysis, alpha])

  const activePreset = useMemo(
    () => presets.find((preset) => preset.id === selectedPreset) ?? null,
    [presets, selectedPreset],
  )

  const metrics = activePreset?.metrics

  const onSelectPreset = (presetId: string) => {
    fetchPresetGeometry(presetId).catch((err) => setError((err as Error).message))
  }

  return (
    <div className="app">
      <header className="hero">
        <div>
          <h1>AeroStack Studio</h1>
          <p className="subtitle">
            Explore curated NACA profiles and run panel analysis with a streamlined interface.
          </p>
        </div>
        <div className="hero-badge">beta</div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <section className="card">
            <h2>Preset library</h2>
            <p className="card-hint">Click an airfoil to load its geometry and recommended angle of attack.</p>
            <div className="preset-list">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  className={
                    'preset-card' + (preset.id === selectedPreset ? ' preset-card--active' : '')
                  }
                  onClick={() => onSelectPreset(preset.id)}
                >
                  <div className="preset-card__title">{preset.label}</div>
                  <div className="preset-card__tags">
                    {preset.tags.map((tag) => (
                      <span key={tag}>{tag}</span>
                    ))}
                  </div>
                  <p>{preset.description}</p>
                </button>
              ))}
            </div>
          </section>

          <section className="card">
            <h2>Custom NACA</h2>
            <label className="field">
              <span>NACA 4-digit code</span>
              <input
                value={digits}
                maxLength={4}
                onChange={(event) => {
                  const value = event.target.value.replace(/[^0-9]/g, '')
                  setDigits(value)
                  setSelectedPreset('custom')
                }}
              />
            </label>
            <div className="field-row">
              <label className="field">
                <span>Points on surface</span>
                <input
                  type="number"
                  value={nPoints}
                  min={60}
                  max={800}
                  onChange={(event) => setNPoints(parseInt(event.target.value || '200', 10))}
                />
              </label>
              <button
                className="secondary"
                onClick={() => {
                  setSelectedPreset('custom')
                  fetchCustomAirfoil().catch((err) => setError((err as Error).message))
                }}
                disabled={digits.length !== 4}
              >
                Generate
              </button>
            </div>
          </section>

          <section className="card">
            <h2>Analysis setup</h2>
            <div className="field-row">
              <label className="field">
                <span>Angle of attack (deg)</span>
                <input
                  type="number"
                  value={alpha}
                  step={0.5}
                  onChange={(event) => setAlpha(parseFloat(event.target.value))}
                />
              </label>
              <label className="field">
                <span>Panels</span>
                <input
                  type="number"
                  value={panels}
                  min={40}
                  max={320}
                  onChange={(event) => setPanels(parseInt(event.target.value || '120', 10))}
                />
              </label>
            </div>
            <div className="metrics">
              <div>
                <span>CL (thin airfoil)</span>
                <strong>{formatNumber(analysis?.cl_thin_airfoil)}</strong>
              </div>
            </div>
            {metrics && (
              <div className="metrics">
                <div>
                  <span>Max camber %</span>
                  <strong>{metrics.max_camber_pct}</strong>
                </div>
                <div>
                  <span>Camber position %</span>
                  <strong>{metrics.max_camber_x_pct}</strong>
                </div>
                <div>
                  <span>Thickness %</span>
                  <strong>{metrics.max_thickness_pct}</strong>
                </div>
              </div>
            )}
          </section>

          {error && <div className="card card--error">{error}</div>}
        </aside>

        <main className="content">
          <section className="panel">
            <header className="panel__header">
              <div>
                <h2>Geometry</h2>
                <p>Surface reconstruction plotted with matched upper and lower traces.</p>
              </div>
              <div className="status-chip">{analysisLoading ? 'solving...' : 'ready'}</div>
            </header>
            {airfoilPlot && <Plot data={airfoilPlot.data} layout={airfoilPlot.layout} className="plot" />}
          </section>

          <section className="panel">
            <header className="panel__header">
              <div>
                <h2>Pressure coefficient</h2>
                <p>Constant-strength vortex panel solution evaluated along the unified surface arc.</p>
              </div>
              <div className="status-chip">{analysisLoading ? 'updating...' : 'fresh'}</div>
            </header>
            {cpPlot && <Plot data={cpPlot.data} layout={cpPlot.layout} className="plot" />}
          </section>
        </main>
      </div>
    </div>
  )
}
