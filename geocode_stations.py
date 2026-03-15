import pandas as pd
from geopy.geocoders import Nominatim
import time
import re

# 1. HISTORICAL TRANSLATION DICTIONARY
# Essential for 1940 East Asian geography
HISTORICAL_MAP = {
    "奉天": "Shenyang Railway Station, China",
    "新京": "Changchun Railway Station, China",
    "京城": "Seoul Station, South Korea",
    "三棵樹": "Harbin East Railway Station, China",
    "安東": "Dandong, China",
    "大連": "Dalian, China",
    "哈爾濱": "Harbin, China",
    "釜山": "Busan, South Korea",
    "下關": "Shimonoseki, Japan",
    "安州": "Anju, North Korea",
    "咸興": "Hamhung, North Korea"
}

def clean_name(name):
    """Removes historical markers from unique_stations.txt."""
    # Remove 'Station' suffix (驛)
    name = re.sub(r'驛$', '', name)
    # Remove 'Bound for' suffix (行)
    name = re.sub(r'行$', '', name)
    # Remove Ferry connection markers like {宇野}
    name = re.sub(r'\{.*\}', '', name)
    return name.strip()

def geocode_all_stations(input_file, output_file):
    geolocator = Nominatim(user_agent="hist_2437_project")
    
    # Read names directly from your uploaded file
    with open(input_file, 'r', encoding='utf-8') as f:
        station_list = [line.strip() for line in f if line.strip()]

    results = []
    print(f"Total stations to process: {len(station_list)}")

    for original_name in station_list:
        name_to_search = clean_name(original_name)
        
        # Check translation dictionary first
        search_query = HISTORICAL_MAP.get(name_to_search, name_to_search)
        
        try:
            # Attempt to find the location
            location = geolocator.geocode(search_query, timeout=10)
            
            if location:
                results.append({
                    "Original_Name": original_name,
                    "Clean_Name": name_to_search,
                    "Latitude": location.latitude,
                    "Longitude": location.longitude,
                    "Found_Address": location.address
                })
                print(f"Found: {name_to_search}")
            else:
                results.append({
                    "Original_Name": original_name,
                    "Clean_Name": name_to_search,
                    "Latitude": None, 
                    "Longitude": None
                })
                print(f"FAILED: {name_to_search}")
            
            # Pause to respect Nominatim's usage policy (1 request per second)
            time.sleep(1.1)
            
        except Exception as e:
            print(f"Error on {name_to_search}: {e}")
            time.sleep(2)

    # Save to CSV for database import
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Saved results to {output_file}")

if __name__ == "__main__":
    geocode_all_stations("results/unique_stations.txt", "geocoded_stations_full.csv")