#!/usr/bin/env python3
"""Pre-filter the large OSM railways GeoJSON to a generous Manchuria bounding box.
Output: openstreetmap/manchuria_railways.geojson
"""
import json
import os

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(PROJ_DIR, 'openstreetmap', 'hotosm_chn_railways_lines_geojson.geojson')
OUTPUT = os.path.join(PROJ_DIR, 'openstreetmap', 'manchuria_railways.geojson')

# Generous Manchuria bbox (with padding)
MINLAT, MAXLAT = 36, 56
MINLON, MAXLON = 116, 136


def coords_in_bbox(coords):
    """Return True if any coordinate in the list falls within the bbox."""
    for c in coords:
        if isinstance(c[0], (list, tuple)):
            # MultiLineString — recurse
            if coords_in_bbox(c):
                return True
        else:
            lon, lat = c[0], c[1]
            if MINLAT <= lat <= MAXLAT and MINLON <= lon <= MAXLON:
                return True
    return False


def main():
    print(f'Filtering {INPUT}')
    print(f'Bbox: lat [{MINLAT}, {MAXLAT}], lon [{MINLON}, {MAXLON}]')

    features = []
    total = 0

    with open(INPUT) as f:
        for line in f:
            if '"type": "Feature"' not in line:
                continue
            total += 1
            try:
                cleaned = line.strip().rstrip(',')
                feat = json.loads(cleaned)
                geom = feat.get('geometry', {})
                raw_coords = geom.get('coordinates', [])
                if coords_in_bbox(raw_coords):
                    features.append(feat)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    print(f'Kept {len(features)}/{total} features')

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    with open(OUTPUT, 'w') as f:
        json.dump(geojson, f)

    sz = os.path.getsize(OUTPUT) / 1e6
    print(f'Wrote {OUTPUT} ({sz:.1f} MB)')


if __name__ == '__main__':
    main()
