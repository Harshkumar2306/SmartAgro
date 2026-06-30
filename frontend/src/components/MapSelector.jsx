import React, { useState } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, FeatureGroup, useMap } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import { Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const MapSelector = ({ setResults, setLoading, loading }) => {
  const [bbox, setBbox] = useState(null);

  const onCreated = (e) => {
    const layer = e.layer;
    const bounds = layer.getBounds();
    // bounds is a LatLngBounds object
    const _bbox = [
      bounds.getWest(),
      bounds.getSouth(),
      bounds.getEast(),
      bounds.getNorth()
    ];
    setBbox(_bbox);
  };

  const handleAnalyze = async () => {
    if (!bbox) return;
    setLoading(true);
    try {
      const response = await axios.post(`${API_URL}/api/analyze-area`, { bbox });
      setResults(response.data);
    } catch (error) {
      console.error(error);
      alert('Error analyzing area: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ height: '400px', width: '100%', borderRadius: '12px', overflow: 'hidden', marginBottom: '1.5rem', border: '1px solid rgba(255,255,255,0.1)' }}>
        <MapContainer center={[20.5937, 78.9629]} zoom={4} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="&copy; OpenStreetMap contributors"
          />
          <FeatureGroup>
            <EditControl
              position="topright"
              onCreated={onCreated}
              draw={{
                polyline: false,
                circle: false,
                circlemarker: false,
                marker: false,
                polygon: true,
                rectangle: true,
              }}
              edit={{ edit: false, remove: true }}
            />
          </FeatureGroup>
        </MapContainer>
      </div>

      {bbox && (
        <div style={{ textAlign: 'center', marginBottom: '1rem', color: '#94a3b8' }}>
          Area selected! Bounding Box: [{bbox.map(n => n.toFixed(2)).join(', ')}]
        </div>
      )}

      <button 
        className="primary-btn" 
        onClick={handleAnalyze} 
        disabled={!bbox || loading}
      >
        {loading ? <><Loader2 className="spinner" size={20} /> Fetching Satellite Data & Analyzing...</> : 'Analyze Selected Area'}
      </button>
    </div>
  );
};

export default MapSelector;
