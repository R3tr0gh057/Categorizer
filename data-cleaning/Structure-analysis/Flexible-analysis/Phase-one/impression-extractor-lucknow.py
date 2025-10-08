import os
import fitz  # PyMuPDF
from tqdm import tqdm
import logging
import re

# --- CONFIGURATION ---
# 1. Set the folders to scan
FOLDERS_TO_SCAN = [
    r"D:\OLD REPORTS\2024",
    r"D:\OLD REPORTS\2025 JAN-JUL"
]

# 2. Set the primary keyword to filter for specific scan types
#    (Change this to "CT head", "CT KUB", etc., for different datasets)
FILTER_KEYWORD = "abdomen"

# 3. Name of the output file
OUTPUT_FILE = FILTER_KEYWORD + "-data-for-analysis-lucknow.txt"

# 4. Keywords that signal the end of the "IMPRESSION" section
STOP_KEYWORDS = [
    'dr.', 'md', 'dnb', 'consultant radiologist', 'provisional report',
    'advice:', 'note:', 'correlation:', 'follow-up:', 'follow up:',
    '*** end of report ***', 'electronically signed', 'page 1 of', 'page 2 of'
]

# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def stream_pdfs(folders_to_scan):
    """A generator that finds PDFs directly inside the specified folders."""
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            tqdm.write(f"Warning: Folder not found, skipping: {folder}")
            continue
        try:
            for filename in os.listdir(folder):
                if filename.lower().endswith('.pdf'):
                    yield os.path.join(folder, filename)
        except Exception as e:
            logging.error(f"Could not read files in folder {folder}: {e}")

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF and returns it as a single lowercase string."""
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE).lower() for page in doc)
    except Exception as e:
        # This will catch MuPDF errors for corrupted files
        tqdm.write(f"  -> Skipping corrupted/unreadable file: {os.path.basename(pdf_path)} ({e})")
        return None

def extract_impression(full_text):
    """Extracts the IMPRESSION section using multi-step logic."""
    if not full_text:
        return None

    # Step 1: Find the Starting Point (Primary and Fallback)
    start_index = -1
    # Primary search for "impression:"
    match = re.search(r'impression:', full_text, re.IGNORECASE)
    if match:
        start_index = match.end()
    else:
        # Fallback search for "impression" as a standalone word/heading
        match = re.search(r'\n\s*impression\s*\n', full_text, re.IGNORECASE)
        if match:
            start_index = match.end()

    if start_index == -1:
        return None # No impression section found

    # Step 2: Find the Ending Point
    # Find the earliest occurrence of any stop keyword after the impression starts
    end_index = len(full_text) # Default to the end of the text
    first_stop_pos = -1

    for keyword in STOP_KEYWORDS:
        try:
            pos = full_text.index(keyword, start_index)
            if first_stop_pos == -1 or pos < first_stop_pos:
                first_stop_pos = pos
        except ValueError:
            continue # Keyword not found
    
    if first_stop_pos != -1:
        end_index = first_stop_pos

    # Step 3: Extract and Clean the Text
    impression_text = full_text[start_index:end_index].strip()
    # Clean up excessive newlines and spaces
    impression_text = re.sub(r'\s+', ' ', impression_text).strip()
    
    return impression_text if impression_text else None

def main():
    """Main function to run the extraction process."""
    print("--- Starting Impression Extraction Script ---")
    
    all_pdfs = list(stream_pdfs(FOLDERS_TO_SCAN))
    if not all_pdfs:
        print("No PDF files found in the specified directories. Exiting.")
        return

    all_impressions = []
    filter_keyword_lower = FILTER_KEYWORD.lower()
    
    with tqdm(total=len(all_pdfs), desc="Processing Reports", unit="file") as pbar:
        for pdf_path in all_pdfs:
            filename = os.path.basename(pdf_path)
            pbar.set_postfix_str(f"Checking: {filename}", refresh=True)

            full_text = extract_text_from_pdf(pdf_path)
            if not full_text:
                pbar.update(1)
                continue

            # Check if the keyword exists in the filename OR the content
            if filter_keyword_lower in filename.lower() or filter_keyword_lower in full_text:
                tqdm.write(f"  -> Match for '{FILTER_KEYWORD}' in '{filename}'. Extracting impression...")
                impression = extract_impression(full_text)
                
                if impression:
                    header = f"--- IMPRESSION FROM: {pdf_path} ---\n"
                    all_impressions.append(header + impression + "\n")
                    tqdm.write("Impression extracted successfully.")
                else:
                    tqdm.write("'Impression' section not found in this report.")
            
            pbar.update(1)

    # Write all found impressions to the output file
    if all_impressions:
        try:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                f.write("\n".join(all_impressions))
            print(f"\nSuccess! Analysis complete. {len(all_impressions)} impressions saved to: {os.path.abspath(OUTPUT_FILE)}")
        except Exception as e:
            print(f"\nError: Could not write report to file. {e}")
    else:
        print(f"\nAnalysis complete. No reports matching the keyword '{FILTER_KEYWORD}' with an impression section were found.")

if __name__ == "__main__":
    main()