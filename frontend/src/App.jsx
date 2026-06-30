import React, { useState } from 'react';
import './index.css';
import { Leaf, Map, Upload } from 'lucide-react';
import MapSelector from './components/MapSelector';
import LocalUploader from './components/LocalUploader';
import Dashboard from './components/Dashboard';

function App() {
  const [activeTab, setActiveTab] = useState('map');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  return (
    <div className="app-container">
      <header>
        <h1>SmartAgro</h1>
      </header>

      {!results ? (
        <div className="glass-panel">
          <div className="tabs">
            <button 
              className={`tab-btn ${activeTab === 'map' ? 'active' : ''}`}
              onClick={() => setActiveTab('map')}
            >
              <Map size={18} style={{ display: 'inline', marginRight: '8px', verticalAlign: 'text-bottom' }} />
              Draw on Map
            </button>
            <button 
              className={`tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
              onClick={() => setActiveTab('upload')}
            >
              <Upload size={18} style={{ display: 'inline', marginRight: '8px', verticalAlign: 'text-bottom' }} />
              Upload GeoTIFFs
            </button>
          </div>

          {activeTab === 'map' ? (
            <MapSelector setResults={setResults} setLoading={setLoading} loading={loading} />
          ) : (
            <LocalUploader setResults={setResults} setLoading={setLoading} loading={loading} />
          )}
        </div>
      ) : (
        <Dashboard results={results} onReset={() => setResults(null)} />
      )}
    </div>
  );
}

export default App;
