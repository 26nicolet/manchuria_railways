import os
import json

def check_json_files(directory):
    total_files = 0
    empty_files = 0
    valid_files = 0
    error_files = 0
    
    print(f"Scanning directory: {directory}")

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                total_files += 1
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if not content:
                            print(f"[EMPTY_CONTENT] {filepath}")
                            empty_files += 1
                            continue
                        
                        data = json.loads(content)
                        
                        if isinstance(data, list) and len(data) == 0:
                             print(f"[EMPTY_LIST] {filepath}")
                             empty_files += 1
                        elif isinstance(data, list):
                            print(f"[VALID_LIST] {filepath} ({len(data)} items)")
                            # meaningful check: first item keys
                            if len(data) > 0 and isinstance(data[0], dict):
                                keys = list(data[0].keys())
                                # print(f"  Keys: {keys}")
                            valid_files += 1
                        elif isinstance(data, dict):
                            print(f"[VALID_DICT] {filepath}")
                            valid_files += 1
                        else:
                            print(f"[UNKNOWN_STRUCTURE] {filepath} Type: {type(data)}")
                            valid_files += 1 # technically valid json

                except json.JSONDecodeError as e:
                    print(f"[JSON_ERROR] {filepath}: {e}")
                    error_files += 1
                except Exception as e:
                    print(f"[READ_ERROR] {filepath}: {e}")
                    error_files += 1

    print("-" * 30)
    print(f"Total JSON files: {total_files}")
    print(f"Empty/Empty List files: {empty_files}")
    print(f"Valid JSON files: {valid_files}")
    print(f"Error files: {error_files}")

if __name__ == "__main__":
    check_json_files("extracted_data")
