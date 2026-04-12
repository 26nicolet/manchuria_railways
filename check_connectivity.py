import json
import numpy as np

# Load station coords
with open('results/all_stations.json') as f:
    stations = json.load(f)

# Check Korean stations
korean_names = ['京城', '安東', '平壤', '開城', '新義州', '仁川', '釜山', '大邱', '大田', '水原']
print("=== Korean station coordinates ===")
for name in korean_names:
    for s in stations:
        if s['name'] == name:
            print(f"  {name}: lat={s['lat']}, lon={s['lon']}, has_trains={s.get('has_trains', False)}")
            break
    else:
        print(f"  {name}: NOT FOUND in stations")

# Check NK synthetic railway endpoints
print("\n=== NK synthetic railway endpoint areas ===")
with open('openstreetmap/selected_railways.geojson') as f:
    geo = json.load(f)

# Find synthetic NK features (they were appended near the end)
nk_features = []
for feat in geo['features']:
    coords = feat['geometry']['coordinates']
    if feat['geometry']['type'] == 'LineString':
        # Check if coords are in NK area (lat 37-41, lon 124-130)
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        if all(37 <= lat <= 41 for lat in lats) and all(124 <= lon <= 130 for lon in lons):
            # Check if it's a synthetic segment (short, few points)
            if len(coords) == 2:
                nk_features.append(coords)

print(f"  Found {len(nk_features)} 2-point segments in NK area")
if nk_features:
    # Get the southernmost endpoint (closest to Seoul)
    south_pts = []
    for coords in nk_features:
        for c in coords:
            south_pts.append((c[1], c[0]))
    south_pts.sort()
    print(f"  Southernmost point: lat={south_pts[0][0]}, lon={south_pts[0][1]}")
    print(f"  Northernmost point: lat={south_pts[-1][0]}, lon={south_pts[-1][1]}")

# Check SK OSM railway coverage
print("\n=== SK OSM railway bbox ===")
sk_lats = []
sk_lons = []
sk_count = 0
for feat in geo['features']:
    if feat['geometry']['type'] == 'LineString':
        coords = feat['geometry']['coordinates']
        for c in coords:
            if 34 <= c[1] <= 38 and 126 <= c[0] <= 130:
                sk_lats.append(c[1])
                sk_lons.append(c[0])
        if any(34 <= c[1] <= 37.7 for c in coords):
            sk_count += 1

if sk_lats:
    print(f"  SK features (south of 37.7): {sk_count}")
    print(f"  SK lat range: {min(sk_lats):.4f} - {max(sk_lats):.4f}")
    print(f"  SK lon range: {min(sk_lons):.4f} - {max(sk_lons):.4f}")
else:
    print("  No SK railway features found!")
