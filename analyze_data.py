#!/usr/bin/env python3
"""Analyze the existing results data and the OSM GeoJSON."""
import json
from collections import Counter

# 1. Check existing stations & trains
with open('results/stations_web.json') as f:
    stations = json.load(f)
print(f'Stations with coords: {len(stations)}')

with open('results/trains.json') as f:
    trains = json.load(f)
print(f'Trains: {len(trains)}')

good = sum(1 for t in trains if len(t['stops']) >= 2)
print(f'Trains with 2+ stops: {good}')

rc = Counter(t['region'] for t in trains)
print('Train regions:', rc)

sc = Counter(s['region'] for s in stations)
print('Station regions:', sc)

# Check a well-formed train
for t in trains:
    if len(t['stops']) >= 5:
        print(f'\nSample train {t["train_no"]} ({t["region"]}): {len(t["stops"])} stops')
        for s in t['stops'][:8]:
            print(f'  {s["station"]} @ {s["time"]} ({s["lat"]:.3f},{s["lon"]:.3f}) {s["type"]}')
        break

# 2. Geography of existing stations
lats = [s['lat'] for s in stations if s['lat']]
lons = [s['lon'] for s in stations if s['lon']]
print(f'\nStation lat range: {min(lats):.2f} - {max(lats):.2f}')
print(f'Station lon range: {min(lons):.2f} - {max(lons):.2f}')

# 3. Analyze OSM GeoJSON quickly - just first 500 lines to understand structure
import ijson  # try streaming
print('\n--- OSM GeoJSON ---')
import os
fsize = os.path.getsize('openstreetmap/hotosm_chn_railways_lines_geojson.geojson')
print(f'File size: {fsize / 1e6:.1f} MB')

# Use simple line counting for rough feature count
print(f'(347K lines per wc -l)')

# Stream a sample of features
count = 0
named_count = 0
sample_named = []
bbox = {'minlat': 90, 'maxlat': -90, 'minlon': 180, 'maxlon': -180}

with open('openstreetmap/hotosm_chn_railways_lines_geojson.geojson') as f:
    # Skip to features array manually
    import re
    buf = ''
    for line in f:
        buf += line
        # Each feature is a single line (check)
        if '"type": "Feature"' in line:
            count += 1
            try:
                # Try to parse this line as JSON
                cleaned = line.strip().rstrip(',')
                feat = json.loads(cleaned)
                name = feat['properties'].get('name', '')
                coords = feat['geometry']['coordinates']
                if coords:
                    c0 = coords[0]
                    bbox['minlon'] = min(bbox['minlon'], c0[0])
                    bbox['maxlon'] = max(bbox['maxlon'], c0[0])
                    bbox['minlat'] = min(bbox['minlat'], c0[1])
                    bbox['maxlat'] = max(bbox['maxlat'], c0[1])
                if name:
                    named_count += 1
                    if len(sample_named) < 20:
                        sample_named.append(f"  {name} | {feat['properties'].get('name:en','')} | {len(coords)} pts")
            except:
                pass
            if count >= 5000:
                break

print(f'Features sampled: {count}')
print(f'Named (in sample): {named_count}')
print(f'BBox: lat {bbox["minlat"]:.2f}-{bbox["maxlat"]:.2f}, lon {bbox["minlon"]:.2f}-{bbox["maxlon"]:.2f}')
print('Sample named:')
for s in sample_named:
    print(s)
