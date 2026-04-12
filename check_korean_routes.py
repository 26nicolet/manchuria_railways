import json

with open('results/route_data.json') as f:
    data = json.load(f)

korean_stations = {'京城', '安東', '平壤', '開城', '新義州', '仁川', '釜山', '大邱', '大田', '水原'}
korean_routes = []
for r in data:
    stops = [s['station'] for s in r['stops']]
    if any(s in korean_stations for s in stops):
        geom_types = r.get('geom_type', [])
        korean_routes.append({
            'train': r['train_no'],
            'stops': stops,
            'geom_type': set(geom_types),
            'region': r.get('region', 'unknown'),
        })

print(f'Found {len(korean_routes)} routes touching Korean stations')
for kr in korean_routes[:30]:
    stop_str = ' -> '.join(kr['stops'][:6])
    if len(kr['stops']) > 6:
        stop_str += '...'
    print(f"  Train {kr['train']}: {stop_str} | geom: {kr['geom_type']} | region: {kr['region']}")
