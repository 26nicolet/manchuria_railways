import os
import time
import io
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai

# ==========================================
# CONFIGURATION
# ==========================================
# Set your API key here (or preferably, set it in your environment variables)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "AIzaSyCsnKHu5pk31dlOIvvLm3DumAXGFaFEL0A"))

# Using gemini-2.5-flash-lite
model = genai.GenerativeModel('gemini-2.5-flash-lite')

PDF_PATH = "1940_schedules.pdf"
OUTPUT_FILE = "extracted_timetables_retry.md"

# Pages that previously returned "NO TIMETABLE DETECTED"
PAGES_TO_RETRY = [
    13, 14, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 
    30, 31, 32, 33, 34, 35, 36, 37, 38, 40, 41, 43, 44, 45, 46, 47, 49, 50, 51, 52, 53, 54, 56, 
    57, 58, 59, 60, 61, 62, 64, 67, 68, 69, 70, 71, 72, 73, 74, 77, 78, 79, 80
]

PROMPT = """
Role: You are an expert Japanese historian and archivist specializing in pre-WWII railway documents. The attached document contains train schedules from 1940, written in traditional Japanese with Kyujitai characters. This also document contains a list of hotels/ryokans. Your task is to extract the train schedules in the attached image into a structured Markdown table. If you see a list of hotels, format them as a Markdown table or a simple list.

Task: Extract the train schedules AND hotel information in the attached image into a structured Markdown table.

Rules for Extraction:
1. Preserve Kyujitai: Output the exact Kanji used in the image (e.g., use 滿, 鐵, 驛, 臺). Do not convert to Shinjitai.
2. Train Timetable Structure: Use Train Numbers/Designations (e.g., 18, 急) as column headers. Use Station Names (驛名) as row names.
3. Hotel Directory Structure: Ensure you capture the Hotel Name, Location/Nearest Station, Room Rates (usually in 圓/Yen or 錢/Sen), Meals included, and any notable amenities or telephone numbers. Format:
| Name (名称) | Location (場所) | Phone (電話) | Price/Notes (備考) |
|---|---|---|---|
| ... | ... | ... | ... |
4. Missing Data: If a train skips a station (↓) or a cell is blank, output "↓" or "N/A" respectively.
5. Annotations: Include small text or fractions next to times in brackets.
6. Filter: Extract ALL tabular data visible. Even if it looks like a fare table or listing, please extract it. Only output "NO TIMETABLE DETECTED" if the page is absolutely just a map or picture with NO text tables. For pages labeled 目次，extract the route names and station names into a Markdown list.

CRITICAL INSTRUCTION:
- The AI has previously entered an infinite loop when reading text on hotels.
- DO NOT REPEAT THE SAME HOTEL TWICE.
- If you see a list of hotels, format them as a Markdown table or a simple list.
- If the page contains advertisements, summary text, or maps in addition to the list, prioritize the LIST of establishments.
- STOP immediately after the last unique entry.

If it's a timetable, standard timetable format applies.
"""

# Extracts timetable data
def extract_pdf_data(pdf_path, output_path):
    print(f"Opening {pdf_path}...")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return

    total_pages = len(doc)
    hotel_start_page = total_pages - 12
    
    print(f"Total pages in document: {total_pages}")
    print(f"Retrying extraction for {len(PAGES_TO_RETRY)} failed pages...\n")

    with open(output_path, 'a', encoding='utf-8') as outfile:
        # Loop through only the specific pages we need to retry
        for page_num_1based in PAGES_TO_RETRY:
            page_num = page_num_1based - 1  # Convert to 0-based index for PyMuPDF
            
            # Safety check
            if page_num >= total_pages or page_num < 0:
                print(f"Skipping page {page_num_1based}: out of range.")
                continue
                
            print(f"Processing page {page_num + 1}...")
            
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300) 
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            
            # --- NEW SMART RETRY LOGIC ---
            success = False
            attempts = 0
            
            while not success and attempts < 3:
                try:
                    response = model.generate_content([PROMPT, img])
                    
                    outfile.write(f"## Page {page_num + 1}\n\n")
                    outfile.write(response.text + "\n\n---\n\n")
                    print(f"Page {page_num + 1} successfully extracted.")
                    success = True
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    # If we hit a 429 quota/rate limit error, pause for 30 seconds and try again
                    if "429" in error_msg or "quota" in error_msg:
                        attempts += 1
                        print(f"Speed limit hit. Pausing 30 seconds to let the API cool down (Attempt {attempts}/3)...")
                        time.sleep(30)
                    else:
                        print(f"Unexpected error on page {page_num + 1}: {e}")
                        outfile.write(f"## Page {page_num + 1}\n\n[ERROR: {e}]\n\n---\n\n")
                        break # Break out of the retry loop for non-quota errors
            
            # Standard pause between every page to prevent triggering the speed limit in the first place
            time.sleep(10) 

    print(f"\nExtraction complete! Data saved to {output_path}")

if __name__ == "__main__":
    extract_pdf_data(PDF_PATH, OUTPUT_FILE)