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

import json

d = json.load(open('results/route_data.json'))

# Find real multi-stop routes with increasing times
count = 0
for r in d:
    stops = r['stops']
    if len(stops) >= 6 and all(stops[i]['time_min'] < stops[i+1]['time_min'] for i in range(len(stops)-1)):
        count += 1
        if count <= 3:
            print(f"--- Train {r['train_no']} (id={r['id']}, {len(stops)} stops) ---")
            for s in stops:
                h, m = divmod(s['time_min'], 60)
                print(f"  {h:02d}:{m:02d}  {s['station']}")
            print()

print(f"Total routes with strictly increasing times: {count}")
print(f"Total routes: {len(d)}")
