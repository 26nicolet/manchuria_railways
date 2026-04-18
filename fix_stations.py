#!/usr/bin/env python3
"""Apply station fixes from fixes.txt to stations_web.json, then rebuild."""
import json
import math
import os

PROJ = os.path.dirname(os.path.abspath(__file__))

# Load stations_web.json
with open(os.path.join(PROJ, 'results', 'stations_web.json')) as f:
    stations = json.load(f)

# Load OSM railway data for snapping
with open(os.path.join(PROJ, 'openstreetmap', 'selected_railways.geojson')) as f:
    osm = json.load(f)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# Collect all railway points
rail_points = []
for feat in osm['features']:
    geom = feat['geometry']
    if geom['type'] == 'LineString':
        for c in geom['coordinates']:
            rail_points.append((c[1], c[0]))
    elif geom['type'] == 'MultiLineString':
        for line in geom['coordinates']:
            for c in line:
                rail_points.append((c[1], c[0]))
print(f"Loaded {len(rail_points)} railway points")

def find_nearest_rail(lat, lon, max_km=50):
    best_dist = float('inf')
    best_pt = None
    for rlat, rlon in rail_points:
        # Quick filter
        if abs(rlat - lat) > 0.5 or abs(rlon - lon) > 0.5:
            continue
        d = haversine_km(lat, lon, rlat, rlon)
        if d < best_dist:
            best_dist = d
            best_pt = (rlat, rlon)
    if best_dist > max_km:
        return None, best_dist
    return best_pt, best_dist

# Build station index
stn_idx = {s['name']: i for i, s in enumerate(stations)}

# === FIXES ===

# 1. 康平 - remove
if '康平' in stn_idx:
    idx = stn_idx['康平']
    print(f"REMOVE: 康平 (was at {stations[idx]['lat']}, {stations[idx]['lon']})")
    stations.pop(idx)
    # Rebuild index
    stn_idx = {s['name']: i for i, s in enumerate(stations)}

# 2. 舒蘭 - wrong location
if '舒蘭' in stn_idx:
    idx = stn_idx['舒蘭']
    old = (stations[idx]['lat'], stations[idx]['lon'])
    stations[idx]['lat'] = 44.40788148354434
    stations[idx]['lon'] = 126.95230987351385
    print(f"MOVE: 舒蘭 from {old} to ({stations[idx]['lat']}, {stations[idx]['lon']})")

# 3. 吉林 - wrong location (43°51′26″N 126°34′17″E)
if '吉林' in stn_idx:
    idx = stn_idx['吉林']
    old = (stations[idx]['lat'], stations[idx]['lon'])
    stations[idx]['lat'] = 43.0 + 51/60 + 26/3600  # 43.857222
    stations[idx]['lon'] = 126.0 + 34/60 + 17/3600  # 126.571389
    print(f"MOVE: 吉林 from {old} to ({stations[idx]['lat']:.6f}, {stations[idx]['lon']:.6f})")

# 4-9. Stations not snapped to train line - find nearest rail point
snap_stations = ['大房身', '其塔木', '城子街', '岔路河', '旅順', '北安']
for name in snap_stations:
    if name not in stn_idx:
        print(f"SKIP: {name} not found")
        continue
    idx = stn_idx[name]
    lat, lon = stations[idx]['lat'], stations[idx]['lon']
    nearest, dist = find_nearest_rail(lat, lon)
    if nearest:
        print(f"SNAP: {name} from ({lat}, {lon}) to ({nearest[0]:.6f}, {nearest[1]:.6f}), was {dist:.2f}km away")
        stations[idx]['lat'] = nearest[0]
        stations[idx]['lon'] = nearest[1]
    else:
        print(f"WARNING: {name} - no rail within 50km (nearest {dist:.1f}km). Removing station.")
        stations.pop(idx)
        stn_idx = {s['name']: i for i, s in enumerate(stations)}

# Save
with open(os.path.join(PROJ, 'results', 'stations_web.json'), 'w') as f:
    json.dump(stations, f, ensure_ascii=False, indent=2)
print(f"\nSaved {len(stations)} stations to stations_web.json")
