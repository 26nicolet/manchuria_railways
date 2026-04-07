#!/usr/bin/env python3
"""
Build web-ready data files from:
1. Raw timetable JSON files in train_time_table/
2. Existing station coordinates in results/stations_web.json
3. OSM railway GeoJSON for route geometry

Output:
- results/route_data.json  (trains with route polylines snapped to rail)
- results/railway_network.json  (simplified railway lines for map background)
- results/all_stations.json  (stations for the map)
"""

import json
import os
import glob
import math
import sys
from collections import defaultdict, Counter

import numpy as np
from scipy.spatial import cKDTree
import networkx as nx

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
TTT_DIR = os.path.join(os.path.expanduser('~'), 'Downloads', 'train_time_table')
RESULTS_DIR = os.path.join(PROJ_DIR, 'results')
OSM_FILE = os.path.join(PROJ_DIR, 'openstreetmap', 'selected_railways.geojson')

# Manchuria bounding box
EA_BBOX = {'minlat': 38, 'maxlat': 54, 'minlon': 118, 'maxlon': 135}


def parse_time_to_minutes(time_str):
    try:
        parts = time_str.split('.')
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        return hours * 60 + minutes
    except:
        return None


# ─────────────────── Step 1: Load timetable ───────────────────

def load_timetable_data():
    all_entries = []
    for fpath in sorted(glob.glob(os.path.join(TTT_DIR, '*.json'))):
        with open(fpath) as f:
            data = json.load(f)
        all_entries.extend(data)
    print(f'  Loaded {len(all_entries)} timetable entries')
    return all_entries


# ─────────────────── Step 2: Load station coordinates ───────────────────

def load_station_coords():
    with open(os.path.join(RESULTS_DIR, 'stations_web.json')) as f:
        data = json.load(f)
    coords = {}
    for s in data:
        if s['lat'] and s['lon']:
            if EA_BBOX['minlat'] < s['lat'] < EA_BBOX['maxlat'] and EA_BBOX['minlon'] < s['lon'] < EA_BBOX['maxlon']:
                coords[s['name']] = {
                    'lat': s['lat'], 'lon': s['lon'], 'region': s['region']
                }
    print(f'  Loaded {len(coords)} stations within Manchuria bbox')
    return coords


# ─────────────────── Step 3: Build train routes ───────────────────

MAX_SPEED_KMH = 150  # max realistic speed for 1940s trains

def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def build_train_routes(entries, station_coords):
    # Deduplicate entries (same train_no, station, time, type)
    seen = set()
    unique_entries = []
    for e in entries:
        key = (e['train_no'], e['station'].strip(), e['time'], e['type'])
        if key not in seen:
            seen.add(key)
            unique_entries.append(e)
    print(f'  Deduplicated {len(entries)} -> {len(unique_entries)} entries')

    by_train = defaultdict(list)
    for e in unique_entries:
        by_train[e['train_no']].append(e)

    routes = []
    route_id = 0

    for train_no, stops_raw in by_train.items():
        processed = []
        for s in stops_raw:
            time_min = parse_time_to_minutes(s['time'])
            if time_min is None:
                continue
            station = s['station'].strip()
            if station not in station_coords:
                continue
            sc = station_coords[station]
            processed.append({
                'station': station,
                'time': s['time'],
                'time_min': time_min,
                'type': s['type'].replace('.', ''),
                'lat': sc['lat'],
                'lon': sc['lon'],
                'region': sc['region'],
            })

        if len(processed) < 2:
            continue

        processed.sort(key=lambda x: x['time_min'])

        # First pass: split on time gaps (as before)
        time_segments = []
        current_seg = [processed[0]]
        for i in range(1, len(processed)):
            prev = processed[i - 1]
            curr = processed[i]
            if (curr['station'] == prev['station'] and curr['type'] == prev['type']
                    and curr['time_min'] == prev['time_min']):
                continue
            time_gap = curr['time_min'] - prev['time_min']
            if time_gap < -120 or time_gap > 720:
                if len(current_seg) >= 2:
                    time_segments.append(current_seg)
                current_seg = [curr]
            else:
                current_seg.append(curr)
        if len(current_seg) >= 2:
            time_segments.append(current_seg)

        # Second pass: split on geographic jumps (speed check)
        segments = []
        for tseg in time_segments:
            current_seg = [tseg[0]]
            for i in range(1, len(tseg)):
                prev = current_seg[-1]
                curr = tseg[i]
                dt_min = curr['time_min'] - prev['time_min']
                if dt_min > 0 and curr['station'] != prev['station']:
                    dist_km = _haversine_km(prev['lat'], prev['lon'],
                                            curr['lat'], curr['lon'])
                    speed = dist_km / (dt_min / 60)
                    if speed > MAX_SPEED_KMH:
                        if len(current_seg) >= 2:
                            segments.append(current_seg)
                        current_seg = [curr]
                        continue
                current_seg.append(curr)
            if len(current_seg) >= 2:
                segments.append(current_seg)

        for seg in segments:
            deduped = [seg[0]]
            for i in range(1, len(seg)):
                if seg[i]['station'] != deduped[-1]['station']:
                    deduped.append(seg[i])
                elif seg[i]['time_min'] != deduped[-1]['time_min']:
                    deduped.append(seg[i])
            if len(deduped) < 2:
                continue
            region_counts = Counter(s['region'] for s in deduped)
            region = region_counts.most_common(1)[0][0]
            routes.append({
                'id': f'{train_no}_{route_id}',
                'train_no': str(train_no),
                'region': region,
                'start_time': deduped[0]['time_min'],
                'end_time': deduped[-1]['time_min'],
                'stops': deduped,
            })
            route_id += 1

    print(f'  Built {len(routes)} route segments from {len(by_train)} train numbers')
    return routes


# ─────────────────── Step 4: Build railway graph from OSM ───────────────────

def load_osm_as_graph(station_coords):
    """Load selected_railways.geojson and build a networkx graph,
    filtering to only features near dataset stations."""
    NEAR_THRESH = 0.3  # ~30 km in degrees

    # Build station KDTree
    stn_pts = np.array([[v['lon'], v['lat']] for v in station_coords.values()])
    stn_tree = cKDTree(stn_pts)

    print('  Loading selected railways GeoJSON...')
    with open(OSM_FILE) as f:
        data = json.load(f)
    features = data['features']
    print(f'  {len(features)} features loaded')

    print('  Building graph (proximity-filtered)...')
    G = nx.Graph()
    kept = 0

    for feat in features:
        coords = feat['geometry']['coordinates']
        if len(coords) < 2:
            continue

        # Sample points for proximity check (endpoints + every 10th)
        sample = [coords[0], coords[-1]] + coords[::10]
        near = False
        for c in sample:
            d, _ = stn_tree.query([c[0], c[1]])
            if d < NEAR_THRESH:
                near = True
                break
        if not near:
            continue

        kept += 1
        prev = None
        for c in coords:
            pt = (round(c[0], 4), round(c[1], 4))
            if prev and pt != prev:
                d = math.sqrt((pt[0]-prev[0])**2 + (pt[1]-prev[1])**2)
                if G.has_edge(prev, pt):
                    if d < G[prev][pt]['weight']:
                        G[prev][pt]['weight'] = d
                else:
                    G.add_edge(prev, pt, weight=d)
            prev = pt

    print(f'  Kept {kept}/{len(features)} features near stations')
    print(f'  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')
    return G


# ─────────────────── Step 5: Snap stations & route on graph ───────────────────

def snap_stations_to_graph(station_coords, G):
    """Snap each station to the nearest node in the railway graph using KDTree."""
    print('  Snapping stations to railway graph...')
    nodes = list(G.nodes())
    node_arr = np.array(nodes)  # shape (N, 2), each row is (lon, lat)
    tree = cKDTree(node_arr)

    MAX_SNAP = 0.25  # ~25km
    station_node = {}  # station_name -> graph node tuple
    snapped = 0

    for name, info in station_coords.items():
        q = np.array([info['lon'], info['lat']])
        dist, idx = tree.query(q)
        if dist < MAX_SNAP:
            station_node[name] = nodes[idx]
            snapped += 1

    print(f'  Snapped {snapped}/{len(station_coords)} stations to graph')

    # Prune graph: only keep connected components that have at least one station
    print('  Pruning graph to station-relevant components...')
    station_nodes_set = set(station_node.values())
    keep_nodes = set()
    kept_comps = 0
    for component in nx.connected_components(G):
        if station_nodes_set & component:
            keep_nodes.update(component)
            kept_comps += 1
    G_pruned = G.subgraph(keep_nodes).copy()
    print(f'  Kept {kept_comps} components: {G_pruned.number_of_nodes()} nodes, {G_pruned.number_of_edges()} edges')

    return station_node, G_pruned


def route_on_graph(routes, G, station_node):
    """For each consecutive station pair on a route, find the shortest path
    through the railway graph. Collect all edges used."""
    print('  Pre-computing connected components...')

    # Map each node to its component ID for fast reachability check
    node_component = {}
    for comp_id, component in enumerate(nx.connected_components(G)):
        for node in component:
            node_component[node] = comp_id
    print(f'  {comp_id + 1} connected components')

    print('  Routing trains on railway graph...')

    used_edges = set()
    snapped = 0
    straight = 0
    unreachable = 0

    path_cache = {}

    # A* heuristic: Euclidean distance (coords are lon/lat degrees)
    def heuristic(a, b):
        return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

    for ri, route in enumerate(routes):
        if ri % 50 == 0:
            print(f'    {ri}/{len(routes)} (snapped={snapped}, straight={straight})...')

        stops = route['stops']
        geometry = []

        for i in range(len(stops) - 1):
            fs, ts = stops[i], stops[i + 1]
            fn = station_node.get(fs['station'])
            tn = station_node.get(ts['station'])

            if fn and tn and fn != tn:
                # Check same connected component first (instant)
                if node_component.get(fn) != node_component.get(tn):
                    unreachable += 1
                    geometry.append([
                        [fs['lat'], fs['lon']],
                        [ts['lat'], ts['lon']]
                    ])
                    straight += 1
                    continue

                cache_key = (fn, tn) if fn < tn else (tn, fn)
                if cache_key in path_cache:
                    cached = path_cache[cache_key]
                    if cached is None:
                        path_nodes = None
                    elif fn > tn:
                        path_nodes = list(reversed(cached))
                    else:
                        path_nodes = list(cached)
                else:
                    try:
                        path_nodes = nx.astar_path(G, fn, tn,
                                                    heuristic=heuristic,
                                                    weight='weight')
                        path_cache[cache_key] = path_nodes
                    except nx.NetworkXNoPath:
                        path_nodes = None
                        path_cache[cache_key] = None

                if path_nodes and len(path_nodes) >= 2:
                    geometry.append([[n[1], n[0]] for n in path_nodes])
                    for j in range(len(path_nodes) - 1):
                        a, b = path_nodes[j], path_nodes[j + 1]
                        edge = (a, b) if a < b else (b, a)
                        used_edges.add(edge)
                    snapped += 1
                    continue

            geometry.append([
                [fs['lat'], fs['lon']],
                [ts['lat'], ts['lon']]
            ])
            straight += 1

        route['geometry'] = geometry

    print(f'  Routed on rail: {snapped}, Straight fallback: {straight} (unreachable: {unreachable})')
    print(f'  Unique rail edges used: {len(used_edges)}')
    return used_edges


# ─────────────────── Step 6: Build display from used edges ───────────────────

def simplify_line(coords, tol):
    if len(coords) <= 2:
        return coords
    first, last = coords[0], coords[-1]
    md, mi = 0, 0
    for i in range(1, len(coords) - 1):
        d = _ptld(coords[i], first, last)
        if d > md:
            md, mi = d, i
    if md > tol:
        left = simplify_line(coords[:mi + 1], tol)
        right = simplify_line(coords[mi:], tol)
        return left[:-1] + right
    return [first, last]


def _ptld(pt, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    if dx == 0 and dy == 0:
        return math.sqrt((pt[0]-a[0])**2 + (pt[1]-a[1])**2)
    t = max(0, min(1, ((pt[0]-a[0])*dx + (pt[1]-a[1])*dy) / (dx*dx + dy*dy)))
    return math.sqrt((pt[0]-a[0]-t*dx)**2 + (pt[1]-a[1]-t*dy)**2)


def build_railway_display(G, used_edges, tol=0.005):
    """Build GeoJSON of the railway lines that trains actually use.
    Merges consecutive used edges into longer polylines for efficiency."""
    print('  Building railway display from used edges...')

    # Build a subgraph of only used edges
    sub = nx.Graph()
    for a, b in used_edges:
        sub.add_edge(a, b)

    # Extract connected components and trace each as a polyline
    features = []
    for component in nx.connected_components(sub):
        subg = sub.subgraph(component)
        # Find a chain through this component using DFS
        # For simple paths (degree <= 2 for all interior nodes), trace linearly
        # Otherwise, extract all edges as individual segments
        
        # Find endpoint nodes (degree 1 or degree > 2)
        endpoints = [n for n in subg.nodes() if subg.degree(n) != 2]
        if not endpoints:
            # It's a cycle — start anywhere
            endpoints = [list(subg.nodes())[0]]

        visited_edges = set()
        for start in endpoints:
            for neighbor in subg.neighbors(start):
                edge = (start, neighbor) if start < neighbor else (neighbor, start)
                if edge in visited_edges:
                    continue
                # Trace a line from start through consecutive degree-2 nodes
                line = [start, neighbor]
                visited_edges.add(edge)
                current = neighbor
                prev = start
                while subg.degree(current) == 2:
                    nexts = [n for n in subg.neighbors(current) if n != prev]
                    if not nexts:
                        break
                    nxt = nexts[0]
                    e = (current, nxt) if current < nxt else (nxt, current)
                    if e in visited_edges:
                        break
                    visited_edges.add(e)
                    line.append(nxt)
                    prev = current
                    current = nxt

                if len(line) >= 2:
                    simp = simplify_line(line, tol)
                    features.append({
                        'type': 'Feature',
                        'geometry': {
                            'type': 'LineString',
                            'coordinates': [[round(p[0], 3), round(p[1], 3)] for p in simp],
                        },
                        'properties': {}
                    })

    geojson = {'type': 'FeatureCollection', 'features': features}
    print(f'  {len(features)} railway line features for display')
    return geojson


# ─────────────────── Main ───────────────────

def main():
    print('=== Step 1: Load timetable data ===')
    entries = load_timetable_data()

    print('\n=== Step 2: Load station coordinates ===')
    station_coords = load_station_coords()

    print('\n=== Step 3: Build train routes ===')
    routes = build_train_routes(entries, station_coords)

    print('\n=== Step 4: Build railway graph from OSM ===')
    G = load_osm_as_graph(station_coords)

    print('\n=== Step 5: Snap stations & route on graph ===')
    station_node, G_pruned = snap_stations_to_graph(station_coords, G)
    del G  # free memory
    used_edges = route_on_graph(routes, G_pruned, station_node)

    print('\n=== Step 6: Build railway display ===')
    railway_geojson = build_railway_display(G_pruned, used_edges)

    print('\n=== Step 7: Build station data ===')
    station_train_counts = Counter()
    for route in routes:
        for stop in route['stops']:
            station_train_counts[stop['station']] += 1

    all_stations = []
    for name, info in station_coords.items():
        all_stations.append({
            'name': name,
            'lat': info['lat'],
            'lon': info['lon'],
            'region': info['region'],
            'train_count': station_train_counts.get(name, 0),
        })
    all_stations.sort(key=lambda s: -s['train_count'])
    active = sum(1 for s in all_stations if s['train_count'] > 0)
    print(f'  {len(all_stations)} stations ({active} with trains)')

    print('\n=== Step 8: Save output ===')
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Simplify route geometry and build compact output
    GEOM_TOL = 0.002  # ~200m simplification tolerance
    compact_routes = []
    for route in routes:
        simplified_geom = []
        for seg in route.get('geometry', []):
            # seg is [[lat,lon], ...] — convert to tuples for simplify_line
            if len(seg) > 2:
                tuples = [(c[1], c[0]) for c in seg]  # (lon, lat) for simplify
                simp = simplify_line(tuples, GEOM_TOL)
                simplified_geom.append([[round(p[1], 4), round(p[0], 4)] for p in simp])
            else:
                simplified_geom.append([[round(c[0], 4), round(c[1], 4)] for c in seg])

        compact_stops = []
        for s in route['stops']:
            compact_stops.append({
                'station': s['station'],
                'time_min': s['time_min'],
                'lat': round(s['lat'], 4),
                'lon': round(s['lon'], 4),
            })

        compact_routes.append({
            'id': route['id'],
            'train_no': route['train_no'],
            'region': route['region'],
            'start_time': route['start_time'],
            'end_time': route['end_time'],
            'stops': compact_stops,
            'geometry': simplified_geom,
        })

    with open(os.path.join(RESULTS_DIR, 'route_data.json'), 'w') as f:
        json.dump(compact_routes, f, ensure_ascii=False, separators=(',', ':'))
    sz = os.path.getsize(os.path.join(RESULTS_DIR, 'route_data.json'))
    print(f'  route_data.json ({len(compact_routes)} routes, {sz/1e6:.1f} MB)')

    with open(os.path.join(RESULTS_DIR, 'railway_network.json'), 'w') as f:
        json.dump(railway_geojson, f, separators=(',', ':'))
    sz = os.path.getsize(os.path.join(RESULTS_DIR, 'railway_network.json'))
    print(f'  railway_network.json ({sz/1e6:.1f} MB)')

    with open(os.path.join(RESULTS_DIR, 'all_stations.json'), 'w') as f:
        json.dump(all_stations, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  all_stations.json')

    print('\n=== Summary ===')
    print(f'  Routes: {len(routes)}')
    print(f'  Stations: {len(all_stations)}')
    print(f'  Railway polylines: {len(railway_geojson["features"])}')
    rc = Counter(r['region'] for r in routes)
    print(f'  Regions: {dict(rc)}')


if __name__ == '__main__':
    sys.setrecursionlimit(50000)
    main()
