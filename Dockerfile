FROM python:3.10-slim

# Install system dependencies required by Rasterio/GDAL
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL version for rasterio compilation
ENV GDAL_CONFIG=/usr/bin/gdal-config

WORKDIR /app

# Copy the requirements file
COPY backend/requirements.txt .

# Install Python dependencies
# Force rasterio to compile against system GDAL to prevent version mismatch segfaults
RUN pip install --no-cache-dir --no-binary rasterio -r requirements.txt

# Copy the entire backend directory
COPY backend/ ./backend/

# Hugging Face Spaces require the app to run on port 7860
ENV PORT=7860
EXPOSE 7860

# Start the FastAPI server using uvicorn
# Single worker to stay within free-tier 2vCPU / 16GB RAM limits
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "7860", "--timeout-keep-alive", "120"]
