import os
import json
import re

def clean_station_name(name):
    # Remove specific symbols often found in OCR failures or timetable annotations
    # 〒: Post office symbol
    # ㊑: Telegraph/Telephone symbol?
    # »: Direction arrow residue
    # ↓: Pass marker
    # …: Ellipsis
    # []: Brackets
    # (): Parentheses
    # \: Escape chars
    # _~・\"\'\.,<>°: Punctuation/symbols
    
    # Regex to remove these characters.
    # Note: re.sub(r'[chars]', '', string)
    cleaned = re.sub(r'[〒㊑»↓…\[\]\(\)_~・\"\'\.,<>°]', '', name)
    cleaned = cleaned.strip()
    return cleaned

def extract_unique_stations(input_dir, output_file):
    unique_stations = set()
    total_files = 0
    
    print(f"Scanning directory: {input_dir}")

    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            continue
                        
                        data = json.loads(content)
                        
                        if isinstance(data, list):
                            total_files += 1
                            for entry in data:
                                if isinstance(entry, dict):
                                    station_name = entry.get('station')
                                    if station_name:
                                        cleaned_name = clean_station_name(station_name)
                                        # Only add if it's not empty and not 'N/A'
                                        if cleaned_name and cleaned_name.lower() != "n/a" and cleaned_name != "":
                                            unique_stations.add(cleaned_name)
                                
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON: {filepath}")
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    sorted_stations = sorted(list(unique_stations))

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for station in sorted_stations:
            f.write(f"{station}\n")

    print("-" * 30)
    print(f"Scanned {total_files} JSON files.")
    print(f"Found {len(sorted_stations)} unique stations.")
    print(f"List saved to {output_file}")
    
    # Print sample
    print("Sample stations (first 50):")
    print(", ".join(sorted_stations[:50]))

if __name__ == "__main__":
    extract_unique_stations("extracted_data", "results/unique_stations.txt")
