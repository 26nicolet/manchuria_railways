import os
import json
import pandas as pd

# CONFIGURATION
STATIONS_CSV = 'results/geocoded_stations_full.csv'
EXTRACTED_DIR = 'extracted_data'
OUTPUT_FILE = 'results/master_railway_database.csv'

def to_minutes(t_str):
    """Converts HH:MM string to minutes from midnight for simulation."""
    try:
        parts = t_str.strip().split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return None

def consolidate_historical_data():
    # 1. Load your spatial ground truth
    stations_df = pd.read_csv(STATIONS_CSV)
    
    all_rows = []
    
    # 2. Walk through the directory structure (page_x/strip_y.json)
    print(f"Searching for JSONs in {EXTRACTED_DIR}...")
    for root, dirs, files in os.walk(EXTRACTED_DIR):
        for file in files:
            if file.endswith('.json'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        # Handle both single objects and lists of objects
                        if isinstance(data, list):
                            all_rows.extend(data)
                        else:
                            all_rows.append(data)
                    except Exception as e:
                        print(f"Error parsing {path}: {e}")

    # 3. Create DataFrame and Join
    schedule_df = pd.DataFrame(all_rows)
    
    # Merge with coordinates on 'station' name
    master_df = pd.merge(
        schedule_df,
        stations_df[['Original_Name', 'Latitude', 'Longitude']],
        left_on='station',
        right_on='Original_Name',
        how='left'
    )

    # 4. Prepare for Simulation
    master_df['time_minutes'] = master_df['time'].apply(to_minutes)
    
    # Sort by Train Number and Time to establish the 'Route Path'
    master_df = master_df.sort_values(by=['train_no', 'time_minutes']).reset_index(drop=True)

    # 5. Export
    master_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"Successfully created {OUTPUT_FILE} with {len(master_df)} records.")

if __name__ == "__main__":
    consolidate_historical_data()