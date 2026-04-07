import json
from collections import Counter

with open('openstreetmap/hotosm_chn_railways_lines_geojson.geojson') as f:
    data = json.load(f)

feats = data['features']
print(f'Total features: {len(feats)}')
print('Property keys:', list(feats[0]['properties'].keys()))

named = sum(1 for f in feats if f['properties'].get('name'))
named_en = sum(1 for f in feats if f['properties'].get('name:en'))
named_zh = sum(1 for f in feats if f['properties'].get('name:zh'))
print(f'Named: {named}, Name EN: {named_en}, Name ZH: {named_zh}')

# Sample named features
count = 0
for f in feats:
    if f['properties'].get('name'):
        coords = f['geometry']['coordinates']
        print(f"  {f['properties']['name']} | en:{f['properties'].get('name:en','')} | zh:{f['properties'].get('name:zh','')} | {len(coords)} pts | ~{coords[0][0]:.1f},{coords[0][1]:.1f}")
        count += 1
        if count >= 30:
            break

# Bounding box
all_lons = []
all_lats = []
for f in feats[:2000]:
    for c in f['geometry']['coordinates']:
        all_lons.append(c[0])
        all_lats.append(c[1])
print(f'Lat range (sample): {min(all_lats):.2f} - {max(all_lats):.2f}')
print(f'Lon range (sample): {min(all_lons):.2f} - {max(all_lons):.2f}')

types = Counter(f['properties'].get('railway', '?') for f in feats)
print('Railway types:', types)
