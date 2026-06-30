import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet-draw';
import { GeoSearchControl, OpenStreetMapProvider } from 'leaflet-geosearch';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import 'leaflet-geosearch/dist/geosearch.css';
import { Loader2, Search } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Fix for missing default icon in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const AdvancedMapControls = ({ setBbox }) => {
  const map = useMap();
  
  useEffect(() => {
    // 1. Setup Search Control
    const provider = new OpenStreetMapProvider();
    const searchControl = new GeoSearchControl({
      provider: provider,
      style: 'bar',
      showMarker: false,
      autoClose: true,
      retainZoomLevel: false,
      animateZoom: true,
      keepResult: true,
      searchLabel: 'Search for farm location...'
    });
    map.addControl(searchControl);

    // 2. Setup Drawing Control
    const drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);
    
    const drawControl = new L.Control.Draw({
      edit: {
        featureGroup: drawnItems,
        remove: true
      },
      draw: {
        polyline: false,
        polygon: {
          allowIntersection: false,
          drawError: { color: '#e1e100', message: '<strong>Oh snap!</strong> you can\'t draw that!' },
          shapeOptions: { color: '#10b981', fillOpacity: 0.3 }
        },
        circle: false,
        marker: false,
        circlemarker: false,
        rectangle: {
          shapeOptions: { color: '#3b82f6', fillOpacity: 0.3 }
        }
      }
    });
    
    map.addControl(drawControl);
    
    map.on(L.Draw.Event.CREATED, (e) => {
      // Clear previous shapes so we only select one area at a time
      drawnItems.clearLayers();
      
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

    map.on(L.Draw.Event.DELETED, () => {
      setBbox(null);
    });

    return () => {
      map.removeControl(searchControl);
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
    <div className="map-selector-container">
      <div className="map-wrapper" style={{ position: 'relative' }}>
        <MapContainer center={[20.5937, 78.9629]} zoom={5} style={{ height: '500px', width: '100%', borderRadius: '16px', zIndex: 1 }}>
          {/* Esri World Imagery (Realistic Satellite Base Map) */}
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
          />
          {/* Optional Overlay for Labels */}
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            attribution=""
          />
          <AdvancedMapControls setBbox={setBbox} />
        </MapContainer>

        {/* Floating Action Panel Over Map */}
        <div className="floating-panel">
          <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
            <Search size={18} color="#3b82f6" /> 
            Select Region
          </h3>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginBottom: '1rem', lineHeight: '1.4' }}>
            Use the search bar on the map to find your farm, then use the polygon tool (⬠) to draw your exact crop boundary.
          </p>
          
          <div className="bounds-display" style={{ 
            background: bbox ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255, 255, 255, 0.05)',
            border: `1px solid ${bbox ? 'rgba(16, 185, 129, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
          }}>
            {bbox ? (
              <span style={{ color: '#10b981', fontFamily: 'monospace', fontSize: '0.85rem' }}>
                W:{bbox[0].toFixed(4)}, S:{bbox[1].toFixed(4)}<br/>
                E:{bbox[2].toFixed(4)}, N:{bbox[3].toFixed(4)}
              </span>
            ) : (
              <span style={{ color: '#64748b' }}>No area selected</span>
            )}
          </div>

          <button 
            className="primary-btn map-analyze-btn" 
            onClick={handleAnalyze} 
            disabled={!bbox || loading}
          >
            {loading ? <><Loader2 className="spinner" size={18} /> Processing Space Data...</> : 'Analyze Selected Area'}
          </button>
        </div>
      </div>
      
      {/* Enhanced Full-Screen Loading Overlay */}
      {loading && (
        <div className="loading-overlay">
          <div className="loading-content">
            <Loader2 className="spinner massive-spinner" size={64} color="#10b981" />
            <h2 className="loading-title">Connecting to Planetary Computer...</h2>
            <p className="loading-subtitle">Fetching multi-spectral Sentinel-2 bands, computing NDVI, and running Machine Learning clusters. This may take a minute for large fields.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MapSelector;
