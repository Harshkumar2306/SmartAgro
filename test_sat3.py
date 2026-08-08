import sys
import numpy as np
import base64
from backend.server import run_satellite_analysis

# Testing another bbox (maybe an agricultural area in season)
bbox = [75.0, 20.0, 75.02, 20.02]

res = run_satellite_analysis(bbox)
print("healthy_pct:", res['stats']['healthy_pct'])

# Let's save the NDVI matrix max/min to see what values we are getting
with open('test_ndvi.jpg', 'wb') as f:
    f.write(base64.b64decode(res['maps']['ndvi_map']))
with open('test_rgb2.jpg', 'wb') as f:
    f.write(base64.b64decode(res['maps']['rgb_map']))

print("Maps saved")
