import json

# Check if railway_network.json already covers the binsuei route (126-131E, 44-46N)
with open('results/railway_network.json') as f:
    net = json.load(f)

net_pts = []
for feat in net['features']:
    for c in feat['geometry']['coordinates']:
        if 126 < c[0] < 131.5 and 44 < c[1] < 46:
            net_pts.append(c)

print(f"railway_network points in binsuei corridor: {len(net_pts)}")

# Load manchuria data and extract binsuei + near-border features
with open('openstreetmap/manchuria_railways.geojson') as f:
    data = json.load(f)

binsuei_feats = []
for feat in data['features']:
    p = feat['properties']
    g = feat['geometry']
    if g['type'] not in ('LineString', 'MultiLineString'):
        continue
    ns = (p.get('name') or '') + (p.get('name:zh') or '')
    if '滨绥' in ns:
        binsuei_feats.append(feat)

# Also get rail features in the corridor that extend east of 131
corridor_feats = []
for feat in data['features']:
    p = feat['properties']
    g = feat['geometry']
    if g['type'] not in ('LineString', 'MultiLineString'):
        continue
    c = g['coordinates'] if g['type'] == 'LineString' else [x for s in g['coordinates'] for x in s]
    lons = [x[0] for x in c]
    lats = [x[1] for x in c]
    rwy = p.get('railway', '')
    if rwy == 'rail' and max(lons) > 131.0 and min(lons) < 131.5 and min(lats) > 44.3 and max(lats) < 44.5:
        corridor_feats.append(feat)

print(f"Binsuei named: {len(binsuei_feats)}")
print(f"Border corridor features: {len(corridor_feats)}")

# Manual Russian connector: Grodekovo border to Vladivostok
# Approximate waypoints based on known route geography
russian_line = {
    "type": "Feature",
    "properties": {"name": "Grodekovo–Vladivostok (Russian section)", "railway": "rail"},
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [131.202, 44.381],  # Suifenhe border (connect to Chinese data endpoint)
            [131.270, 44.393],  # Grodekovo/Pogranichny crossing
            [131.380, 44.420],  # Grodekovo station (Russia)
            [131.420, 44.200],
            [131.420, 43.900],
            [131.430, 43.730],  # near Baranovsky
            [131.420, 43.530],  # Razdolnoye area
            [131.500, 43.480],
            [131.780, 43.480],  # Nadezhdinskaya
            [131.970, 43.370],  # Ugolnaya
            [131.990, 43.250],
            [131.900, 43.200],
            [131.880, 43.115]   # Vladivostok
        ]
    }
}

# Combine all features
all_feats = binsuei_feats + corridor_feats + [russian_line]
# Deduplicate by osm_id
seen = set()
deduped = []
for f in all_feats:
    oid = f.get('properties', {}).get('osm_id')
    if oid and oid in seen:
        continue
    if oid:
        seen.add(oid)
    deduped.append(f)

print(f"Total features in output: {len(deduped)}")

out = {"type": "FeatureCollection", "features": deduped}
with open('results/harbin_vladivostok_railway.geojson', 'w') as f:
    json.dump(out, f)
print("Saved results/harbin_vladivostok_railway.geojson")
