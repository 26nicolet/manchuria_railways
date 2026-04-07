#!/usr/bin/env python3
"""Find train segments with unrealistic speeds."""
import json, math

with open('results/route_data.json') as f:
    routes = json.load(f)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

fast_segments = []
for route in routes:
    stops = route['stops']
    for i in range(len(stops) - 1):
        s1, s2 = stops[i], stops[i + 1]
        dist_km = haversine(s1['lat'], s1['lon'], s2['lat'], s2['lon'])
        dt_min = s2['time_min'] - s1['time_min']
        if dt_min <= 0:
            continue
        speed_kmh = dist_km / (dt_min / 60)
        if speed_kmh > 200:
            fast_segments.append({
                'train': route['train_no'],
                'route_id': route['id'],
                'from': s1['station'],
                'to': s2['station'],
                'dist_km': round(dist_km, 1),
                'time_min': dt_min,
                'speed_kmh': round(speed_kmh, 1),
            })

fast_segments.sort(key=lambda x: -x['speed_kmh'])

print(f"Segments with speed > 200 km/h ({len(fast_segments)} total):\n")
print(f"{'Train':>8} {'From':>14} {'To':>14} {'Dist(km)':>10} {'Time(min)':>10} {'Speed(km/h)':>12}")
print("-" * 72)
for s in fast_segments[:50]:
    print(f"{s['train']:>8} {s['from']:>14} {s['to']:>14} {s['dist_km']:>10} {s['time_min']:>10} {s['speed_kmh']:>12}")

trains = sorted(set(s['train'] for s in fast_segments))
print(f"\nAffected trains ({len(trains)}): {trains}")

# Also check: what's a reasonable max? Show speed distribution
all_speeds = []
for route in routes:
    stops = route['stops']
    for i in range(len(stops) - 1):
        s1, s2 = stops[i], stops[i + 1]
        dist_km = haversine(s1['lat'], s1['lon'], s2['lat'], s2['lon'])
        dt_min = s2['time_min'] - s1['time_min']
        if dt_min > 0 and dist_km > 0.5:
            all_speeds.append(dist_km / (dt_min / 60))

all_speeds.sort()
n = len(all_speeds)
print(f"\nSpeed distribution across all {n} segments:")
for pct in [50, 75, 90, 95, 99, 100]:
    idx = min(int(n * pct / 100), n - 1)
    print(f"  P{pct}: {all_speeds[idx]:.0f} km/h")
