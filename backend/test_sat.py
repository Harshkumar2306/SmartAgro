import sys
sys.path.append('.')
from backend.server import run_satellite_analysis
import base64

try:
    # Example bbox in India
    bbox = [78.9629, 20.5937, 78.9829, 20.6137]
    res = run_satellite_analysis(bbox)
    print("NDVI mean:", res['stats']['healthy_pct'])
    with open('test_rgb.jpg', 'wb') as f:
        f.write(base64.b64decode(res['maps']['rgb_map']))
    print("Success")
except Exception as e:
    print("Error:", e)
