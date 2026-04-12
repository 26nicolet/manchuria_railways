#!/usr/bin/env python3
"""Create approximate railway LineStrings for North Korea based on
historical station locations and known rail routes (Gyeongui Line etc).
Appends features to selected_railways.geojson."""
import json
import os

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTED = os.path.join(PROJ_DIR, 'openstreetmap', 'selected_railways.geojson')

# Historical railway routes through North Korea, defined as ordered station waypoints.
# Coordinates are [lon, lat] (GeoJSON convention).
# Sources: historical Gyeongui Line (京義線), Pyeongra Line, Pyeongnam Line

# Main line: Andong (Dandong) → Sinuiju → Pyongyang → Kaesong → Seoul
# 京義本線 (Gyeongui Main Line)
gyeongui_main = [
    [124.3822, 40.1238],  # 安東 (Andong/Dandong)
    [124.3543, 40.1027],  # 振興
    [124.4344, 40.0708],  # 南新義州
    [124.4000, 40.1000],  # 新義州 (approximate)
    [124.6728, 39.9865],  # 廣里
    [124.9189, 39.7983],  # 宣川
    [125.3078, 39.6070],  # 古邑
    [125.5972, 39.6482],  # 孟中里
    [125.6611, 39.6174],  # 安州
    [125.6063, 39.5963],  # 新安州
    [125.6188, 39.4111],  # 肅川
    [125.6506, 39.3274],  # 漁波
    [125.6836, 39.1958],  # 順安
    [125.7255, 39.0531],  # 西平壤
    [125.7359, 39.0047],  # 平壤
    [125.7763, 38.9195],  # 力浦
    [125.7606, 38.6945],  # 黃州
    [126.0258, 38.4595],  # 興水
    [126.1732, 38.4251],  # 瑞興
    [126.2301, 38.4194],  # 新幕
    [126.3218, 38.3758],  # 物開
    [126.4528, 38.2267],  # 漢浦
    [126.5630, 37.9710],  # 開城 (approximate - historical Kaesong station)
    [126.8542, 38.4266],  # 臨津江 - skip, this is on a different branch
]

# Corrected main line without the Imjin branch jump
gyeongui_corrected = [
    [124.3822, 40.1238],  # 安東
    [124.3543, 40.1027],  # 振興
    [124.4000, 40.1000],  # 新義州 area
    [124.4344, 40.0708],  # 南新義州
    [124.6728, 39.9865],  # 廣里
    [124.9189, 39.7983],  # 宣川
    [125.3078, 39.6070],  # 古邑
    [125.5972, 39.6482],  # 孟中里
    [125.6611, 39.6174],  # 安州
    [125.6063, 39.5963],  # 新安州
    [125.6188, 39.4111],  # 肅川
    [125.9373, 39.4227],  # 順川
    [125.6506, 39.3274],  # 漁波
    [125.6836, 39.1958],  # 順安
    [125.7255, 39.0531],  # 西平壤
    [125.7359, 39.0047],  # 平壤
    [125.7763, 38.9195],  # 力浦
    [125.7606, 38.6945],  # 黃州
    [126.0258, 38.4595],  # 興水
    [126.1732, 38.4251],  # 瑞興
    [126.2301, 38.4194],  # 新幕
    [126.3218, 38.3758],  # 物開
    [126.4528, 38.2267],  # 漢浦/汗浦
    [126.5630, 37.9710],  # 開城 (approximate)
    [126.7500, 37.8000],  # 汶山 area (approximate)
    [126.9069, 37.5154],  # 永登浦
    [126.9420, 37.5142],  # 鷺梁津
    [126.9722, 37.5548],  # 京城 (Seoul)
]

# Pyeongnam branch: 平壤 → 大同江 area, Yangdeok line
pyeongnam_east = [
    [125.7359, 39.0047],  # 平壤
    [126.1449, 39.5653],  # 大同江
    [126.1784, 40.0391],  # 妙香山
]

# Pyeongra branch: 平壤 area east to 陽德
pyeongra = [
    [125.7359, 39.0047],  # 平壤
    [125.9373, 39.4227],  # 順川
    [125.9083, 39.6530],  # 泉洞
    [125.8888, 39.7035],  # 价川
    [126.6458, 39.2167],  # 陽德
]

# Gyeongwon branch: Seoul → Uijeongbu (京元線)
gyeongwon = [
    [126.9722, 37.5548],  # 京城
    [127.0115, 37.5719],  # 東大門
    [127.0372, 37.5612],  # 往十里
    [127.0461, 37.7377],  # 議政府
    [126.8542, 38.4266],  # 臨津江 area (then north toward Wonsan)
    [127.2635, 38.4384],  # 福溪
    [127.4309, 38.9120],  # 龍池院
    [127.3990, 39.7848],  # 定平
    [126.7973, 39.4245],  # 耀德
]

# Seoul local: Incheon branch
incheon_branch = [
    [126.9069, 37.5154],  # 永登浦
    [126.9722, 37.5548],  # 京城
    [126.9754, 37.5600],  # 南大門
    [126.9369, 37.5552],  # 新村
]

# Haeju branch from 黃州 area
haeju = [
    [125.7606, 38.6945],  # 黃州
    [124.9685, 38.7493],  # 德島
]

def make_feature(coords, name):
    return {
        "type": "Feature",
        "properties": {"name": name, "source": "historical_approximation"},
        "geometry": {"type": "LineString", "coordinates": coords}
    }

# Build features - break long routes into segments for better graph connectivity
def segmentize(coords, name):
    """Break a route into individual 2-point segments for graph building."""
    features = []
    for i in range(len(coords) - 1):
        features.append(make_feature(
            [coords[i], coords[i+1]],
            f"{name}_seg{i}"
        ))
    return features

all_new = []
all_new.extend(segmentize(gyeongui_corrected, "gyeongui_main"))
all_new.extend(segmentize(pyeongnam_east, "pyeongnam_east"))
all_new.extend(segmentize(pyeongra, "pyeongra"))
all_new.extend(segmentize(gyeongwon, "gyeongwon"))
all_new.extend(segmentize(incheon_branch, "incheon"))
all_new.extend(segmentize(haeju, "haeju"))

print(f"Created {len(all_new)} synthetic railway segments")

# Load and append to selected_railways.geojson
print(f"Loading {SELECTED}...")
with open(SELECTED) as f:
    selected = json.load(f)

before = len(selected['features'])
selected['features'].extend(all_new)
print(f"Features: {before} -> {len(selected['features'])}")

with open(SELECTED, 'w') as f:
    json.dump(selected, f)

sz = os.path.getsize(SELECTED) / 1e6
print(f"Saved ({sz:.1f} MB)")
