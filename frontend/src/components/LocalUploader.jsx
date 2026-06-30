import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Upload, Loader2, FileImage } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const LocalUploader = ({ setResults, setLoading, loading }) => {
  const [b04, setB04] = useState(null);
  const [b08, setB08] = useState(null);

  const handleAnalyze = async () => {
    if (!b04 || !b08) return;
    setLoading(true);
    
    const formData = new FormData();
    formData.append('b04', b04);
    formData.append('b08', b08);

    try {
      const response = await axios.post(`${API_URL}/api/analyze-local`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResults(response.data);
    } catch (error) {
      console.error(error);
      alert('Error analyzing files: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const FileCard = ({ label, file, setFile }) => (
    <div 
      className={`upload-zone ${file ? 'active' : ''}`}
      onClick={() => document.getElementById(`upload-${label}`).click()}
    >
      <input 
        id={`upload-${label}`}
        type="file" 
        accept=".tif,.tiff" 
        style={{ display: 'none' }}
        onChange={(e) => setFile(e.target.files[0])}
      />
      {file ? (
        <>
          <FileImage size={40} className="upload-icon" style={{ color: '#10b981' }} />
          <h3 style={{ color: '#f8fafc' }}>{file.name}</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Ready</p>
        </>
      ) : (
        <>
          <Upload size={40} className="upload-icon" />
          <h3 style={{ color: '#f8fafc' }}>Upload {label} Band</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.5rem' }}>Select a GeoTIFF (.tif) file</p>
        </>
      )}
    </div>
  );

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
        <FileCard label="B04 (Red)" file={b04} setFile={setB04} />
        <FileCard label="B08 (NIR)" file={b08} setFile={setB08} />
      </div>

      <button 
        className="primary-btn" 
        onClick={handleAnalyze} 
        disabled={!b04 || !b08 || loading}
      >
        {loading ? <><Loader2 className="spinner" size={20} /> Processing Imagery...</> : 'Analyze Local Data'}
      </button>
    </div>
  );
};

export default LocalUploader;
