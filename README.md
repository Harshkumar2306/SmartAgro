---
title: Smart Agro API
emoji: 🌍
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
---

# SmartAgro 🌍

SmartAgro is a highly advanced, full-stack Precision Agriculture platform that combines Live Satellite Imagery, Unsupervised Machine Learning, and Hyper-local Weather APIs to give farmers and agronomists real-time, actionable insights on crop health and resource management.

## 🏗️ Architecture Stack

### 1. The Frontend (React + Vite)
- **UI/UX:** Built with React and Lucide icons, featuring a futuristic "glassmorphism" design system tailored for a premium AgTech feel.
- **Mapping:** Uses `Leaflet` and `react-leaflet` to render a fully interactive global map.
- **Auto-Cropping:** Features intelligent geo-spatial tools that allow users to safely draw bounding boxes around farms without crashing the server via massive data requests.
- **Deployment:** Deployed globally on Vercel for instant load times.

### 2. The Backend (Python + FastAPI)
- **Engine:** Built with FastAPI, running a multi-threaded asynchronous architecture.
- **Heavy ML Isolation:** Remote sensing and machine learning tasks (GDAL/Rasterio/Scikit-Learn) are executed in isolated background subprocesses (`SATELLITE_WORKER_SCRIPT`) to prevent C-level segfaults and thread-blocking.
- **Deployment:** Hosted on Hugging Face Spaces using a Docker container, scaling effortlessly to handle complex ML workloads.

## 🧠 Core Intelligence Modules

### A. Multi-Spectral Remote Sensing (Space Data)
The backend directly connects to the **Microsoft Planetary Computer** via `pystac_client` to search for **Sentinel-2 L2A** satellite imagery.
- It dynamically finds the most recent cloud-free image of the farm.
- If a farm crosses the boundary of a satellite tile, the API seamlessly **mosaics (stitches)** multiple tiles together using `rasterio` and `numpy` arrays.

### B. Machine Learning Vegetation Indices
Using the Red, Near-Infrared (NIR), and Green light bands from space, we mathematically calculate:
- **NDVI (Normalized Difference Vegetation Index):** Measures photosynthetic health (vigor).
- **NDWI (Normalized Difference Water Index):** Measures surface and canopy moisture.
- **SAVI (Soil Adjusted Vegetation Index):** Corrects NDVI for sparse crops where soil is visible.

### C. Unsupervised Clustering (ML Stress Map)
We pass the raw NDVI matrix into a **K-Means Clustering** algorithm (`scikit-learn`). The AI autonomously classifies every pixel into three distinct clusters without human labeling:
- 🟢 **Healthy** (High Vigor)
- 🟡 **Moderate** (Transitioning/Struggling)
- 🔴 **Stressed** (Bare soil, severe drought, or disease)

### D. Live Environmental APIs
The system pulls live meteorological data (Temperature, Humidity, Rain) via **Open-Meteo**, and regional data via **OpenStreetMap (Nominatim)** reverse geocoding.

### E. AI Action Plan & Resource Optimizer
The AI cross-references the satellite indices with the live weather to generate actionable insights:
- **Resource Optimizer:** Calculates exactly how many Metric Tons of Nitrogen/Urea are needed to recover the "Stressed" zones, and calculates the exact water deficit in cubic meters.
- **Predictive Disease Radar:** If the API detects high live humidity and temperature *combined* with high satellite moisture, it triggers a warning for potential fungal/pathogen outbreaks.
- **Yield Predictor:** Uses an agronomic heuristic algorithm to estimate final crop yield (MT/ha) based on current canopy health and stress penalties.
