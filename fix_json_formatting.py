import os
import json

def fix_json_formatting(directory):
    fixed_count = 0
    error_count = 0
    skipped_count = 0

    print(f"Scanning directory for markdown-wrapped JSON: {directory}")

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    lines = content.splitlines()
                    if not lines:
                        skipped_count += 1
                        continue

                    original_lines_count = len(lines)
                    modified = False

                    # Check for start marker
                    if lines[0].strip().startswith("```"):
                        print(f"Found start marker in {filepath}")
                        lines.pop(0)
                        modified = True
                    
                    # Check for end marker (need to re-check length in case it was a 1-line file)
                    if lines and lines[-1].strip() == "```":
                         print(f"Found end marker in {filepath}")
                         lines.pop(-1)
                         modified = True
                    
                    if modified:
                        new_content = "\n".join(lines).strip()
                        
                        # Verify it is valid JSON before saving
                        try:
                            json.loads(new_content)
                            with open(filepath, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            print(f"[FIXED] {filepath}")
                            fixed_count += 1
                        except json.JSONDecodeError as e:
                            print(f"[FAILED_VALIDATION] {filepath} after stripping markers: {e}")
                            # logic: maybe we stripped too much or not enough? 
                            # If it was invalid before, and is invalid now, we didn't break it worse, but didn't fix it.
                            error_count += 1
                    else:
                        skipped_count += 1

                except Exception as e:
                    print(f"[ERROR] processing {filepath}: {e}")
                    error_count += 1

    print("-" * 30)
    print(f"Fixed files: {fixed_count}")
    print(f"Skipped files: {skipped_count}")
    print(f"Errors/Failed validation: {error_count}")

if __name__ == "__main__":
    fix_json_formatting("extracted_data")
