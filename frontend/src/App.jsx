import { useState } from 'react';
import { Leaf, Map, Upload } from 'lucide-react';
import './index.css';
import MapSelector from './components/MapSelector';
import LocalUploader from './components/LocalUploader';
import Dashboard from './components/Dashboard';

export default function App() {
  const [mode, setMode] = useState('map');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const reset = () => { setResults(null); setError(''); setLoading(false); };

  return (
    <main className="app-shell">
      <header className="app-header">
        <a className="brand" href="#top" aria-label="AgroSight home">
          <span className="brand-mark"><Leaf size={22} aria-hidden="true" /></span>
          <span>Agro<span>Sight</span></span>
        </a>
        <p className="header-note">Satellite-informed field screening</p>
      </header>
      <section id="top" className="workspace" aria-busy={loading}>
        {results ? <Dashboard results={results} onReset={reset} /> : <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <p className="lede" style={{ margin: 0, fontSize: '0.9rem' }}>Select a bounding box or upload Red and NIR GeoTIFFs.</p>
            <div className="source-tabs" role="tablist" aria-label="Analysis source" style={{ marginBottom: 0 }}>
              <button className={mode === 'map' ? 'active' : ''} onClick={() => { setMode('map'); setError(''); }} role="tab" aria-selected={mode === 'map'}><Map size={17} /> Satellite area</button>
              <button className={mode === 'upload' ? 'active' : ''} onClick={() => { setMode('upload'); setError(''); }} role="tab" aria-selected={mode === 'upload'}><Upload size={17} /> Local GeoTIFFs</button>
            </div>
          </div>
          {error && <div className="status-message error" role="alert">{error}</div>}
          {mode === 'map'
            ? <MapSelector setResults={setResults} setLoading={setLoading} loading={loading} setError={setError} />
            : <LocalUploader setResults={setResults} setLoading={setLoading} loading={loading} setError={setError} />}
        </>}
      </section>
    </main>
  );
}
