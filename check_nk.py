#!/usr/bin/env python3
"""Find trains between Andong and Korean stations, and identify
the North Korea corridor stations needed."""
import json, glob, os
from collections import defaultdict

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
TTT_DIR = os.path.expanduser('~/Downloads/train_time_table')

with open(os.path.join(PROJ_DIR, 'results', 'stations_web.json')) as f:
    stations = json.load(f)

stn_by_name = {s['name']: s for s in stations if s['lat'] and s['lon']}
korea_stns = {s['name'] for s in stations if s.get('region') == 'korea'}

all_entries = []
for fpath in sorted(glob.glob(os.path.join(TTT_DIR, '*.json'))):
    with open(fpath) as f:
        data = json.load(f)
    all_entries.extend(data)

by_train = defaultdict(list)
for e in all_entries:
    by_train[e['train_no']].append(e)

print("=== Trains visiting both 安東 and Korean stations ===")
nk_stations_seen = set()
for tn, entries in sorted(by_train.items()):
    stns = set(e['station'].strip() for e in entries)
    has_andong = '安東' in stns or '安東驛' in stns
    has_korea = bool(stns & korea_stns)
    if has_andong and has_korea:
        sorted_entries = sorted(entries, key=lambda e: e['time'])
        route_stns = []
        for e in sorted_entries:
            name = e['station'].strip()
            if name in stn_by_name:
                s = stn_by_name[name]
                if 124 < s['lon'] < 128 and 37 < s['lat'] < 41:
                    route_stns.append(f"{name}({e['time']})")
                    nk_stations_seen.add(name)
        if route_stns:
            print(f"  Train {tn}: {' -> '.join(route_stns[:20])}")

print(f"\n=== All stations in NK corridor (lat 37.5-40.2, lon 124-127.5) ===")
nk_corridor = [s for s in stations if s['lat'] and s['lon']
               and 37.5 < s['lat'] < 40.2 and 124 < s['lon'] < 127.5]
nk_corridor.sort(key=lambda s: -s['lat'])
for s in nk_corridor:
    marker = " ***" if s['name'] in nk_stations_seen else ""
    print(f"  {s['name']:>10}  lat={s['lat']:.4f}  lon={s['lon']:.4f}  region={s['region']}{marker}")
