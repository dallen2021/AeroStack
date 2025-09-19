import { useEffect, useMemo, useState } from 'react';
import Plot from 'react-plotly.js';
import './App.css';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';
const DEFAULT_ALPHA_RANGE = [-10, -6, -2, 0, 2, 4, 8, 12];

function formatNumber(value, fractionDigits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—';
  }
  return Number.parseFloat(value).toFixed(fractionDigits);
}

export default function App() {
  const [nacaCode, setNacaCode] = useState('2412');
  const [alpha, setAlpha] = useState(0);
  const [panelCount, setPanelCount] = useState(80);
  const [chord, setChord] = useState(1.0);
  const [thicknessScale, setThicknessScale] = useState(1.0);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isCodeValid = useMemo(() => /^\d{4}$/.test(nacaCode), [nacaCode]);

  useEffect(() => {
    if (!isCodeValid) {
      setError('NACA code must be four digits (e.g. 2412).');
      return;
    }
    setError('');
    const controller = new AbortController();
    const timer = setTimeout(() => {
      const payload = {
        naca_code: nacaCode,
        alpha_deg: alpha,
        panel_count: panelCount,
        alpha_curve: DEFAULT_ALPHA_RANGE
      };
      setLoading(true);
      fetch(`${API_BASE}/api/analysis`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      })
        .then(async (response) => {
          if (!response.ok) {
            const message = await response.text();
            throw new Error(message || 'Failed to run analysis');
          }
          return response.json();
        })
        .then((data) => {
          setAnalysis(data);
          setLoading(false);
        })
        .catch((err) => {
          if (err.name === 'AbortError') {
            return;
          }
          setError(err.message || 'Failed to run analysis');
          setLoading(false);
        });
    }, 200);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [alpha, nacaCode, panelCount, isCodeValid]);

  const downloadDXF = async () => {
    const params = new URLSearchParams({
      naca_code: nacaCode,
      chord: String(chord),
      thickness_scale: String(thicknessScale),
      panel_count: String(panelCount)
    });
    try {
      const response = await fetch(`${API_BASE}/api/export/dxf?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to export DXF');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `NACA${nacaCode}.dxf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>AeroStack</h1>
        <p>Parametric airfoil explorer with thin-airfoil and vortex panel solvers.</p>
      </header>
      <section className="controls">
        <div className="control">
          <label htmlFor="nacaCode">NACA 4-digit</label>
          <input
            id="nacaCode"
            value={nacaCode}
            onChange={(event) => setNacaCode(event.target.value.trim())}
            maxLength={4}
          />
        </div>
        <div className="control">
          <label htmlFor="alpha">Angle of attack (°)</label>
          <input
            id="alpha"
            type="range"
            min={-10}
            max={15}
            step={0.25}
            value={alpha}
            onChange={(event) => setAlpha(Number.parseFloat(event.target.value))}
          />
          <span>{formatNumber(alpha, 2)}°</span>
        </div>
        <div className="control">
          <label htmlFor="panels">Panel count</label>
          <input
            id="panels"
            type="range"
            min={20}
            max={100}
            step={2}
            value={panelCount}
            onChange={(event) => setPanelCount(Number.parseInt(event.target.value, 10))}
          />
          <span>{panelCount}</span>
        </div>
        <div className="control">
          <label htmlFor="chord">Chord (m)</label>
          <input
            id="chord"
            type="number"
            min={0.05}
            step={0.05}
            value={chord}
            onChange={(event) => setChord(Number.parseFloat(event.target.value) || 0)}
          />
        </div>
        <div className="control">
          <label htmlFor="thicknessScale">Thickness scale</label>
          <input
            id="thicknessScale"
            type="number"
            min={0.2}
            step={0.1}
            value={thicknessScale}
            onChange={(event) => setThicknessScale(Number.parseFloat(event.target.value) || 0)}
          />
        </div>
        <button type="button" onClick={downloadDXF} disabled={!isCodeValid}>
          Export DXF
        </button>
      </section>
      {error && <p className="error">{error}</p>}
      {loading && <p className="loading">Crunching panels…</p>}
      {analysis && !loading && (
        <>
          <section className="metrics">
            <div>
              <span className="metric-label">C<sub>L</sub> (thin)</span>
              <span>{formatNumber(analysis.thin_airfoil.cl)}</span>
            </div>
            <div>
              <span className="metric-label">C<sub>L</sub> (vortex)</span>
              <span>{formatNumber(analysis.vortex_panel.cl)}</span>
            </div>
            <div>
              <span className="metric-label">α<sub>0</sub> (°)</span>
              <span>{formatNumber(analysis.thin_airfoil.alpha_l0_deg)}</span>
            </div>
            <div>
              <span className="metric-label">Solver time (ms)</span>
              <span>{formatNumber(analysis.metrics.solver_time_ms, 1)}</span>
            </div>
            <div>
              <span className="metric-label">C<sub>L</sub> error vs baseline</span>
              <span>{formatNumber(analysis.metrics.cl_error_baseline)}</span>
            </div>
            <div>
              <span className="metric-label">Memory</span>
              <span>{(analysis.metrics.memory_bytes / 1024).toFixed(1)} kB</span>
            </div>
          </section>
          <section className="plots">
            <div className="plot">
              <Plot
                data={[
                  {
                    x: analysis.airfoil.upper.x,
                    y: analysis.airfoil.upper.y,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Upper'
                  },
                  {
                    x: analysis.airfoil.lower.x,
                    y: analysis.airfoil.lower.y,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Lower'
                  }
                ]}
                layout={{
                  title: 'Airfoil geometry',
                  xaxis: { title: 'x/c', range: [0, 1] },
                  yaxis: { title: 'y/c', scaleanchor: 'x', scaleratio: 1 },
                  margin: { t: 40, r: 10, b: 40, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '100%' }}
              />
            </div>
            <div className="plot">
              <Plot
                data={[
                  {
                    x: analysis.thin_airfoil.alpha_range,
                    y: analysis.thin_airfoil.cl_curve,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Thin-airfoil'
                  },
                  {
                    x: [alpha],
                    y: [analysis.vortex_panel.cl],
                    type: 'scatter',
                    mode: 'markers',
                    marker: { size: 10 },
                    name: 'Vortex panel'
                  }
                ]}
                layout={{
                  title: 'Lift coefficient vs α',
                  xaxis: { title: 'α (°)' },
                  yaxis: { title: 'C_L', automargin: true },
                  margin: { t: 40, r: 10, b: 40, l: 50 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '100%' }}
              />
            </div>
            <div className="plot">
              <Plot
                data={[
                  {
                    x: analysis.vortex_panel.cp_x,
                    y: analysis.vortex_panel.cp,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Cp'
                  }
                ]}
                layout={{
                  title: 'Surface pressure (Cp)',
                  xaxis: { title: 'x/c' },
                  yaxis: { title: 'Cp', autorange: 'reversed' },
                  margin: { t: 40, r: 10, b: 40, l: 60 }
                }}
                config={{ displayModeBar: false }}
                style={{ width: '100%', height: '100%' }}
              />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
