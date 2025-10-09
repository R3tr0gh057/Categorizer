import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import re
import argparse

# --- CONFIGURATION ---
# Folder with PDFs directly inside (no subfolders)
REPORTS_FOLDER = r"D:\DATA\Desktop\Reports"
# Folder with nested patient folders that contain PDFs
MAIN_FOLDER = r"E:\InnoWave_Data\filestore" 

# The keyword to filter for specific scan types
FILTER_KEYWORD = "abdomen"

# Name of the output file
OUTPUT_FILE = FILTER_KEYWORD + "-data-for-analysis-deep.txt"

# Keywords that signal the end of the "IMPRESSION" section
STOP_KEYWORDS = [
    'dr.', 'md', 'dnb', 'consultant radiologist', 'provisional report',
    'advice:', 'note:', 'correlation:', 'follow-up:', 'follow up:',
    '*** end of report ***', 'electronically signed', 'page 1 of', 'page 2 of'
]

# --- NEW FEATURE: INDEX FILE ---
INDEX_FILE = "pdf_index.txt"


# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def stream_pdfs(folders_to_scan):
    """
    A generator that finds and 'yields' one PDF path at a time.
    It uses os.walk to correctly search through both flat and nested directories.
    """
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            tqdm.write(f"Warning: Folder not found, skipping: {folder}")
            continue
        # os.walk traverses the entire directory tree, making it perfect for both folder structures.
        for root, _, files in os.walk(folder, topdown=True):
            for file in files:
                if file.lower().endswith('.pdf'):
                    yield os.path.join(root, file)

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF and returns it as a single lowercase string."""
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE).lower() for page in doc)
    except Exception as e:
        tqdm.write(f"  -> Skipping corrupted/unreadable file: {os.path.basename(pdf_path)} ({e})")
        return None

def extract_impression(full_text):
    """Extracts the IMPRESSION section using multi-step logic."""
    if not full_text:
        return None

    start_index = -1
    # Attempt 1 (Primary): Search for "impression:"
    match = re.search(r'impression:', full_text, re.IGNORECASE)
    if match:
        start_index = match.end()
    else:
        # Attempt 2 (Fallback): Search for "impression" as a standalone word/heading
        match = re.search(r'\n\s*impression\s*\n', full_text, re.IGNORECASE)
        if match:
            start_index = match.end()

    if start_index == -1:
        return None

    end_index = len(full_text)
    first_stop_pos = -1

    for keyword in STOP_KEYWORDS:
        try:
            pos = full_text.index(keyword, start_index)
            if first_stop_pos == -1 or pos < first_stop_pos:
                first_stop_pos = pos
        except ValueError:
            continue
    
    if first_stop_pos != -1:
        end_index = first_stop_pos

    impression_text = full_text[start_index:end_index].strip()
    impression_text = re.sub(r'\s+', ' ', impression_text).strip()
    
    return impression_text if impression_text else None

def main():
    """Main function to run the extraction process."""
    print("--- Starting Impression Extraction Script ---")
    
    # --- ADDED FEATURE LOGIC: INDEXING ---
    all_pdfs = []
    if os.path.exists(INDEX_FILE):
        print(f"Loading file paths from existing index '{INDEX_FILE}'...")
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            all_pdfs = [line.strip() for line in f if line.strip()]
    else:
        print("No index file found. Creating one now (this may take a few minutes)...")
        folders_to_scan = [REPORTS_FOLDER, MAIN_FOLDER]
        all_pdfs = list(tqdm(stream_pdfs(folders_to_scan), desc="Indexing PDF files"))
        try:
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                for path in all_pdfs:
                    f.write(path + '\n')
            print(f"Index file '{INDEX_FILE}' created successfully.")
        except Exception as e:
            print(f"Could not write index file: {e}")
    # --- END OF ADDED FEATURE LOGIC ---

    if not all_pdfs:
        print("No PDF files found in the specified directories. Exiting.")
        return
    print(f"Discovery complete. Found {len(all_pdfs)} PDF files.\n")

    all_impressions = []
    filter_keyword_lower = FILTER_KEYWORD.lower()
    
    print("Phase 2: Analyzing report content...")
    with tqdm(total=len(all_pdfs), desc="Processing Reports", unit="file") as pbar:
        for pdf_path in all_pdfs:
            filename = os.path.basename(pdf_path)
            pbar.set_postfix_str(f"Checking: {filename}", refresh=False)

            full_text = extract_text_from_pdf(pdf_path)
            if not full_text:
                pbar.update(1)
                continue

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