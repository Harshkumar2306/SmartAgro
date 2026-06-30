import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, FeatureGroup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet-draw';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import { Loader2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DrawControl = ({ setBbox }) => {
  const map = useMap();
  
  useEffect(() => {
    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    
    const drawControl = new L.Control.Draw({
      edit: {
        featureGroup: drawnItems
      },
      draw: {
        polyline: false,
        polygon: true,
        circle: false,
        marker: false,
        circlemarker: false,
        rectangle: true
      }
    });
    
    map.addControl(drawControl);
    
    map.on(L.Draw.Event.CREATED, (e) => {
      drawnItems.addLayer(e.layer);
      const bounds = e.layer.getBounds();
      const _bbox = [
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth()
      ];
      setBbox(_bbox);
    });

    return () => {
      map.removeControl(drawControl);
      map.removeLayer(drawnItems);
    };
  }, [map, setBbox]);

  return null;
};

const MapSelector = ({ setResults, setLoading, loading }) => {
  const [bbox, setBbox] = useState(null);

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
          <DrawControl setBbox={setBbox} />
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
