# Manchuria 1940 Railways
# Copyright (C) 2026 Nicole Tian
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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
