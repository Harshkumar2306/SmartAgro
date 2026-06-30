FROM python:3.10-slim

# Do NOT install system gdal-bin/libgdal-dev — it conflicts with rasterio's bundled GDAL
# and causes segfaults. Rasterio wheels ship their own libgdal.
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the requirements file
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory
COPY backend/ ./backend/

# Hugging Face Spaces require the app to run on port 7860
ENV PORT=7860
EXPOSE 7860

# Start the FastAPI server using uvicorn with 2 workers for resilience
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2", "--timeout-keep-alive", "120"]
