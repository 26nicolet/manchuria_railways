"""
Preprocesses master_railway_database.csv into clean JSON for the web visualization.

Key challenges:
- Train numbers are reused across different railway systems (Japan, Korea, Taiwan, Manchuria)
- Need to split into geographically coherent route segments
- Need valid coordinates and parseable times
"""
import csv
import json
import math
from collections import defaultdict

INPUT_CSV = 'results/master_railway_database.csv'
OUTPUT_JSON = 'results/trains.json'
OUTPUT_STATIONS_JSON = 'results/stations_web.json'

MAX_SEGMENT_GAP_KM = 300  # If consecutive stops are > this distance, split into new route


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_time_minutes(t_str):
    """Parse HH:MM to minutes from midnight. Returns None if unparseable."""
    if not t_str or t_str in ('↓', 'N/A', '', '―', '-'):
        return None
    try:
        parts = t_str.strip().split(':')
        h, m = int(parts[0]), int(parts[1])
        return h * 60 + m
    except (ValueError, IndexError):
        return None


def classify_region(lat, lon):
    """Rough classification of a coordinate into a railway region."""
    if lat is None or lon is None:
        return 'unknown'
    if 38 <= lat <= 54 and 118 <= lon <= 136:
        return 'manchuria'
    if 33 <= lat <= 46 and 124 <= lon <= 132:
        return 'korea'
    if 21.5 <= lat <= 25.5 and 120 <= lon <= 122:
        return 'taiwan'
    if 30 <= lat <= 46 and 128 <= lon <= 146:
        return 'japan'
    if 18 <= lat <= 42 and 100 <= lon <= 125:
        return 'china'
    return 'other'


def main():
    # Step 1: Read CSV
    rows_by_train = defaultdict(list)
    all_stations = {}

    with open(INPUT_CSV, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            train_no = row.get('train_no', '').strip()
            station = row.get('station', '').strip()
            time_str = row.get('time', '').strip()
            stop_type = row.get('type', '').strip()
            lat_str = row.get('Latitude', '').strip()
            lon_str = row.get('Longitude', '').strip()
            line = row.get('line', '').strip()

            if not train_no or not station:
                continue

            # Only keep trains with purely numeric train numbers
            if not train_no.isdigit():
                continue

            # Parse coordinates
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except (ValueError, TypeError):
                continue

            time_min = parse_time_minutes(time_str)
            if time_min is None:
                continue

            rows_by_train[train_no].append({
                'station': station,
                'time': time_str,
                'time_min': time_min,
                'type': stop_type,
                'lat': lat,
                'lon': lon,
                'line': line,
            })

            # Collect unique stations
            if station not in all_stations:
                all_stations[station] = {'lat': lat, 'lon': lon, 'region': classify_region(lat, lon)}

    print(f"Read {sum(len(v) for v in rows_by_train.values())} stops for {len(rows_by_train)} train numbers")

    # Step 2: For each train, sort by time and split into coherent route segments
    routes = []
    route_id = 0

    for train_no, stops in rows_by_train.items():
        # Sort by time
        stops.sort(key=lambda s: s['time_min'])

        # Split into segments when distance jumps
        segments = []
        current_segment = [stops[0]]

        for i in range(1, len(stops)):
            prev = current_segment[-1]
            curr = stops[i]
            dist = haversine_km(prev['lat'], prev['lon'], curr['lat'], curr['lon'])

            if dist > MAX_SEGMENT_GAP_KM:
                # Start a new segment
                if len(current_segment) >= 2:
                    segments.append(current_segment)
                current_segment = [curr]
            else:
                current_segment.append(curr)

        if len(current_segment) >= 2:
            segments.append(current_segment)

        # Create route entries (only if segment has 2+ distinct stations)
        for seg in segments:
            # Check that there are at least 2 distinct station names
            unique_stations = set(s['station'] for s in seg)
            if len(unique_stations) < 2:
                continue
            # Check that there are at least 2 distinct coordinates
            unique_coords = set((s['lat'], s['lon']) for s in seg)
            if len(unique_coords) < 2:
                continue

            # Validate that consecutive stops have realistic speeds
            # 1940s trains max ~150 km/h; allow 200 km/h to be safe
            MAX_SPEED_KMH = 200
            valid = True
            for i in range(len(seg) - 1):
                a, b = seg[i], seg[i + 1]
                dist = haversine_km(a['lat'], a['lon'], b['lat'], b['lon'])
                time_diff = b['time_min'] - a['time_min']
                if time_diff <= 0:
                    continue  # same-minute stops are ok (Arr/Dep pairs)
                speed = dist / (time_diff / 60.0)
                if speed > MAX_SPEED_KMH:
                    valid = False
                    break
            if not valid:
                continue

            # Require at least 3 stops, OR 2 stops with at least 1 Arr
            # (a segment of 2 Dep stops with no Arr is likely fragmented data)
            if len(seg) == 2:
                types = set(s['type'] for s in seg)
                if 'Arr' not in types:
                    continue

            region = classify_region(seg[0]['lat'], seg[0]['lon'])
            routes.append({
                'id': f"{train_no}_{route_id}",
                'train_no': train_no,
                'region': region,
                'line': seg[0].get('line', ''),
                'start_time': seg[0]['time_min'],
                'end_time': seg[-1]['time_min'],
                'stops': [{
                    'station': s['station'],
                    'time': s['time'],
                    'time_min': s['time_min'],
                    'type': s['type'],
                    'lat': s['lat'],
                    'lon': s['lon'],
                } for s in seg]
            })
            route_id += 1

    print(f"Created {len(routes)} route segments")

    # Step 3: Region stats
    region_counts = defaultdict(int)
    for r in routes:
        region_counts[r['region']] += 1
    print("Routes by region:")
    for region, count in sorted(region_counts.items(), key=lambda x: -x[1]):
        print(f"  {region}: {count}")

    # Step 4: Build stations JSON (with train counts)
    station_trains = defaultdict(set)
    for r in routes:
        for s in r['stops']:
            station_trains[s['station']].add(r['train_no'])

    stations_out = []
    for name, info in all_stations.items():
        stations_out.append({
            'name': name,
            'lat': info['lat'],
            'lon': info['lon'],
            'region': info['region'],
            'train_count': len(station_trains.get(name, set())),
        })

    # Step 5: Write outputs
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(routes, f, ensure_ascii=False)
    print(f"Wrote {OUTPUT_JSON} ({len(routes)} routes)")

    with open(OUTPUT_STATIONS_JSON, 'w', encoding='utf-8') as f:
        json.dump(stations_out, f, ensure_ascii=False)
    print(f"Wrote {OUTPUT_STATIONS_JSON} ({len(stations_out)} stations)")


if __name__ == '__main__':
    main()
