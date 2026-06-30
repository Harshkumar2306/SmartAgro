import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';
import '@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css';
import { GeoSearchControl, OpenStreetMapProvider } from 'leaflet-geosearch';
import 'leaflet/dist/leaflet.css';
import 'leaflet-geosearch/dist/geosearch.css';
import { Loader2, Search } from 'lucide-react';

// Force connection to Hugging Face (ignores Vercel's old environment variables)
const API_URL = 'https://harsh0o23-smart-agro-api.hf.space';

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

    // 2. Setup Geoman Drawing Control (Much more reliable than leaflet-draw)
    map.pm.addControls({
      position: 'topleft',
      drawMarker: false,
      drawCircleMarker: false,
      drawPolyline: false,
      drawPolygon: true,
      drawRectangle: true,
      drawCircle: false,
      drawText: false,
      editMode: true,
      dragMode: false,
      cutPolygon: false,
      removalMode: true,
    });

    // Handle creation
    map.on('pm:create', (e) => {
      // Clear other layers to keep only one bounding box
      map.eachLayer((layer) => {
        if (layer.pm && layer !== e.layer && layer._path) {
          layer.remove();
        }
      });
      
      const bounds = e.layer.getBounds();
      const _bbox = [
        bounds.getWest(),
        bounds.getSouth(),
        bounds.getEast(),
        bounds.getNorth()
      ];
      setBbox(_bbox);
      
      // Listen for edits on this specific layer
      e.layer.on('pm:edit', () => {
        const newBounds = e.layer.getBounds();
        setBbox([
          newBounds.getWest(),
          newBounds.getSouth(),
          newBounds.getEast(),
          newBounds.getNorth()
        ]);
      });
    });
    
    // Handle deletion
    map.on('pm:remove', () => {
      setBbox(null);
    });

    return () => {
      map.removeControl(searchControl);
      map.pm.removeControls();
      // Remove all drawn shapes on unmount
      map.eachLayer((layer) => {
        if (layer.pm && layer._path) {
          layer.remove();
        }
      });
    };
  }, [map, setBbox]);

  return null;
};

const MapSelector = ({ setResults, setLoading, loading }) => {
  const [bbox, setBbox] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState("Connecting to Planetary Computer...");

  const handleAnalyze = async () => {
    if (!bbox) return;
    setLoading(true);
    setLoadingMessage("Initiating satellite link...");
    try {
      // 1. Start the async job
      const response = await axios.post(`${API_URL}/api/analyze-async`, { bbox }, { timeout: 30000 });
      const jobId = response.data.job_id;
      
      // 2. Poll the status with generous retries
      let retryCount = 0;
      const MAX_RETRIES = 20;  // Much more patient - satellite downloads can take time
      let notFoundCount = 0;

      const checkStatus = async () => {
        try {
           const statusRes = await axios.get(`${API_URL}/api/status/${jobId}`, { timeout: 15000 });
           const status = statusRes.data.status;
           
           // Reset retry count on any successful response
           retryCount = 0;
           notFoundCount = 0;
           
           if (status === 'completed') {
               setResults(statusRes.data.data);
               setLoading(false);
           } else if (status === 'error') {
               alert('Analysis error: ' + statusRes.data.detail);
               setLoading(false);
           } else {
               const progressMsgs = [
                 "Connecting to Planetary Computer satellite network...",
                 "Downloading multi-spectral Sentinel-2 imagery...",
                 "Processing NDVI, NDWI, and SAVI vegetation indices...",
                 "Running ML clustering for crop health zones...",
                 "Generating map visualizations..."
               ];
               const msgIdx = Math.min(Math.floor(retryCount / 2), progressMsgs.length - 1);
               setLoadingMessage(progressMsgs[msgIdx]);
               retryCount++;
               setTimeout(checkStatus, 3000);
           }
        } catch (err) {
           console.error("Poll error:", err);
           
           // If it's a 404, the job might not be registered yet OR the server restarted
           if (err.response && err.response.status === 404) {
              notFoundCount++;
              // Give it 3 chances - the job might just not be registered yet
              if (notFoundCount < 3) {
                setLoadingMessage("Waiting for satellite processing to begin...");
                setTimeout(checkStatus, 4000);
                return;
              }
              alert("The server restarted during processing. Please try again - the server is now ready.");
              setLoading(false);
              return;
           }
           
           // For network errors (502, timeout, dropped connection) - retry generously
           if (retryCount < MAX_RETRIES) {
              retryCount++;
              setLoadingMessage(`Satellite link unstable, reconnecting... (attempt ${retryCount}/${MAX_RETRIES})`);
              setTimeout(checkStatus, 4000);
           } else {
              alert("Connection to satellite server timed out. Please try again.");
              setLoading(false);
           }
        }
      };
      
      setTimeout(checkStatus, 3000); // Wait 3s before first poll
      
    } catch (error) {
      console.error(error);
      if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
        alert('Cannot reach the satellite server. It may be starting up - please wait 30 seconds and try again.');
      } else {
        alert('Error initiating analysis: ' + error.message);
      }
      setLoading(false);
    }
  };


  return (
    <div className="map-selector-container">
      <div className="map-wrapper" style={{ position: 'relative' }}>
        <MapContainer center={[20.5937, 78.9629]} zoom={5} style={{ height: '500px', width: '100%', borderRadius: '16px', zIndex: 1 }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
          />
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
            attribution=""
          />
          <AdvancedMapControls setBbox={setBbox} />
        </MapContainer>

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
      
      {loading && (
        <div className="loading-overlay">
          <div className="loading-content">
            <Loader2 className="spinner massive-spinner" size={64} color="#10b981" />
            <h2 className="loading-title">{loadingMessage}</h2>
            <p className="loading-subtitle">Fetching multi-spectral Sentinel-2 bands, computing NDVI, and running Machine Learning clusters. This may take a minute for large fields.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default MapSelector;
