import os
import io
import time
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai

# ==========================================
# CONFIGURATION
# ==========================================
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "api_key_here"))
model = genai.GenerativeModel('gemini-2.5-pro')

PDF_PATH = "1940_schedules.pdf"
OUTPUT_BASE_DIR = "extracted_data"

# STRIP SETTINGS: Pair the station anchor with train columns
# Percentage-based cropping (0.0 to 1.0)
STATION_ANCHOR_LEFT = 0.45 
STATION_ANCHOR_RIGHT = 0.55

PROMPT = """
Role: Expert Japanese Historian and Data Architect.
Task: Extract railway timetable and tourism data from this vertical strip.

STRICT DATA RULES:
1. ANCHOR: Use the central station column (驛名) to identify the row.
2. TRAIN DATA: Extract every train number at the top of the columns in this strip.
3. OUTPUT FORMAT: Return a JSON array of objects.
   Example: {"train_no": "15", "station": "奉天", "time": "12:30", "type": "Dep"}
4. CHARACTERS: Use exact Kyujitai (驛, 滿, 鐵, 臺). No modern Shinjitai.
5. LOGIC: Use "↓" for passing/skipping. Omit rows where the train has no entry.
6. INFRASTRUCTURE: If you see hotel/restaurant lists (旅館/食堂), include them as:
   {"category": "Hotel", "name": "NAME", "location": "STATION", "notes": "..."}

CRITICAL INSTRUCTION:
- The AI has previously entered an infinite loop when reading text on hotels.
- DO NOT REPEAT THE SAME HOTEL TWICE.
- If the page contains advertisements, summary text, or maps in addition to the list, prioritize the LIST of establishments or schedules.
- STOP immediately after the last unique entry.

Output ONLY valid JSON. No markdown backticks.
"""

def process_pdf_in_strips(pdf_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)

    for page_num in range(12, total_pages):
        page_idx = page_num + 1
        print(f"--- Processing Page {page_idx}/{total_pages} ---")
        
        # 1. Convert PDF Page to High-Res Image
        page = doc.load_page(page_num)
        pix = page.get_pixmap(dpi=300)
        full_img = Image.open(io.BytesIO(pix.tobytes("png")))
        w, h = full_img.size

        # 2. Define Strips: Left Half + Stations, then Stations + Right Half
        # This ensures the station "anchor" is present in every API call
        strips = [
            (0, 0, STATION_ANCHOR_RIGHT * w, h), # Left page + Anchor
            (STATION_ANCHOR_LEFT * w, 0, w, h)   # Anchor + Right page
        ]

        page_folder = os.path.join(output_dir, f"page_{page_idx:03d}")
        os.makedirs(page_folder, exist_ok=True)

        for s_idx, box in enumerate(strips):
            print(f"  Extracting Strip {s_idx + 1}...")
            strip_img = full_img.crop(box)
            
            img_byte_arr = io.BytesIO()
            strip_img.save(img_byte_arr, format='PNG')

            try:
                # 3. Call Gemini 1.5 Pro
                response = model.generate_content([
                    PROMPT, 
                    {"mime_type": "image/png", "data": img_byte_arr.getvalue()}
                ])
                
                # 4. Save individual strip JSON
                output_file = os.path.join(page_folder, f"strip_{s_idx + 1}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                # Pause to respect API rate limits (adjust based on tier)
                time.sleep(10) 
            except Exception as e:
                print(f"  Error on Page {page_idx}, Strip {s_idx+1}: {e}")

    print("\nExtraction complete. Data organized by page in:", output_dir)

if __name__ == "__main__":
    process_pdf_in_strips(PDF_PATH, OUTPUT_BASE_DIR)