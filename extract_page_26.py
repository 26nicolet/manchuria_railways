import os
import io
import time
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai

# ==========================================
# CONFIGURATION
# ==========================================
# Use the provided API key
genai.configure(api_key="AIzaSyChtqmfJnnnMlmww9eREE7AjACGAo_XtaU")

model = genai.GenerativeModel('models/gemini-2.5-pro')

PDF_PATH = "1940_schedules.pdf"
OUTPUT_DIR = "extracted_data/page_026"

# STRIP SETTINGS: Overlap the center to ensure stations are visible in both
STATION_ANCHOR_LEFT = 0.45 
STATION_ANCHOR_RIGHT = 0.55

PROMPT = """
Extract railway data from this Japanese timetable. 
1. Identify the station column (labeled '驛名').
2. For each train column (identified by a number like 502, 524, 588 at the top):
   - Map EVERY row in that column to the corresponding station name.
   - If the cell contains '↓', record it as {"time": null, "type": "Pass"}.
   - If a station has two times (top and bottom), the top is 'Arr' and the bottom is 'Dep'.
   - If a cell contains an unrecognized symbol, skip that train route.
   - Preserve Kyujitai characters (e.g., 驛, 滿).
Return a JSON list of objects with keys: train_no, station, time, type.
"""

# PROMPT = """
# Role: Expert Japanese Historian and Data Architect.
# Task: Extract railway timetable data from this image strip.

# CRITICAL INSTRUCTION: COLUMN-BY-COLUMN EXTRACTION
# You MUST extract data one TRAIN COLUMN at a time.
# DO NOT read row-by-row across the page.
# 1. Find the first Train Number at the top of a column.
# 2. Go DOWN that SINGLE column, row by row, extracting the time for each station.
# 3. Only when you reach the bottom of that column, move to the next Train Number column.

# CONTEXT:
# - The dark column on the left side of the page contains Station Names (驛名).
# - Columns to the left and right are Train Routes. You only care about the columns to the right.
# - Each vertical column corresponds to ONE Train Number (e.g., 503, 102).

# STEP-BY-STEP:
# 1. Identify a Train Column (look for the number at the top).
# 2. Traverse DOWN that column ENTIRELY. From the first Station Name row ALL THE WAY until the LAST Station Name row. For each cell:
#    - If it has a time, match it to that row's Station Name.
#    - If it is blank or has "...", skip.
#    - If it has "↓", it is a pass (skip or mark as pass).
# 3. Create an entry for every stop found in that column.
# 4. Repeat for the next vertical Train Column.

# REQUIRED JSON FORMAT:
# [
#   {"train_no": "503", "station": "朝陽", "time": "7.24", "type": "Dep"},
#   {"train_no": "503", "station": "NextStation", "time": "8.00", "type": "Dep"},
#   ...
#   {"train_no": "102", "station": "朝陽", "time": "9.15", "type": "Dep"}
# ]

# RULES:
# - PRESERVE Kyujitai characters (e.g., 驛, 滿, 鐵).
# - Time format: "HH.MM" or "HH:MM".
# - Left Strip Image: Station names are on the LEFT side. Train columns are to the RIGHT.
# - Right Strip Image: Station names are on the LEFT side. Train columns are to the RIGHT.
# - STRICTLY PROCESS ONE TRAIN COLUMN FULLY BEFORE STARTING THE NEXT.

# Output ONLY valid JSON.
# """

def extract_page_26(pdf_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    # Page 26 is index 25
    page_num = 25 
    print(f"--- Processing Page 26 (Index {page_num}) ---")
    
    page = doc.load_page(page_num)
    pix = page.get_pixmap(dpi=400)
    full_img = Image.open(io.BytesIO(pix.tobytes("png")))
    w, h = full_img.size

    # Define Strips: 
    # 1. Left Half extended to include the center station column
    # 2. Right Half extended to include the center station column
    strips = [
        (0, 0, int(STATION_ANCHOR_RIGHT * w), h),      # Left Strip
        (int(STATION_ANCHOR_LEFT * w), 0, w, h)   # Right Strip
    ]

    for s_idx, box in enumerate(strips):
        strip_name = "left" if s_idx == 0 else "right"
        print(f"  Extracting {strip_name} strip...")
        
        strip_img = full_img.crop(box)
        
        # Save crop for debugging/verification
        debug_img_path = os.path.join(output_dir, f"debug_strip_{strip_name}.png")
        strip_img.save(debug_img_path)

        img_byte_arr = io.BytesIO()
        strip_img.save(img_byte_arr, format='PNG')

        try:
            print("    Sending to Gemini...")
            response = model.generate_content([
                PROMPT, 
                {"mime_type": "image/png", "data": img_byte_arr.getvalue()}
            ])
            
            # Clean response text (remove potential markdown markers)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()

            output_file = os.path.join(output_dir, f"strip_{strip_name}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(clean_text)
            
            print(f"    Saved to {output_file}")
            
            # Pause to respect API rate limits
            time.sleep(5) 
        except Exception as e:
            print(f"  Error on Strip {strip_name}: {e}")

    print("\nExtraction complete.")

if __name__ == "__main__":
    extract_page_26(PDF_PATH, OUTPUT_DIR)
