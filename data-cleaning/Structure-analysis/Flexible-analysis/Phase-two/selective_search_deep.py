import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import re
import argparse # Added for command-line arguments

# --- CONFIGURATION ---
# Folder with PDFs directly inside (no subfolders)
REPORTS_FOLDER = r"D:\DATA\Desktop\Reports"
# Folder with nested patient folders that contain PDFs
MAIN_FOLDER = r"E:\InnoWave_Data\filestore" 

# Default search terms if none are specified via arguments
SEARCH_TERMS = [
    "subacute appendicitis",
    "Appendicitis with collection",
    "Rupture appendicitis",
    "Chronic appendicitis",
    "Acute pancreatitis",
    "Chronic pancreatitis",
    "Acute pancreatitis with modified CTSI score",
    "Acute pancreatitis with collection",
]

OUTPUT_FILE = "search_report_results_updated.txt"
# --- NEW FEATURE: INDEX FILE ---
INDEX_FILE = "pdf_index.txt"


# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def stream_pdfs(folders_to_scan):
    """
    A generator that finds and 'yields' one PDF path at a time.
    It uses os.walk to search through all subdirectories in the given folders.
    """
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            tqdm.write(f"Warning: Folder not found, skipping: {folder}")
            continue
        for root, _, files in os.walk(folder, topdown=True):
            for file in files:
                if file.lower().endswith('.pdf'):
                    yield os.path.join(root, file)

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF and returns it as a single lowercase string."""
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text").lower() for page in doc)
    except Exception as e:
        tqdm.write(f"  -> Skipping corrupted/unreadable file: {os.path.basename(pdf_path)} ({e})")
        return None

def find_and_process_pdfs(all_pdfs, terms_to_search, filter_keyword=None):
    """
    Finds and processes PDFs, applying positive match logic for each term.
    Optionally filters PDFs by a keyword in the filename or content.
    """
    print("Starting analysis... Press Ctrl+C to stop.")
    
    match_counts = {term: 0 for term in terms_to_search}
    match_files = {term: set() for term in terms_to_search}
    
    if filter_keyword:
        print(f"Filtering for reports containing '{filter_keyword}'...")
        filtered_pdfs = []
        filter_keyword_lower = filter_keyword.lower()
        for pdf_path in tqdm(all_pdfs, desc="Filtering PDFs", unit="pdf"):
            filename = os.path.basename(pdf_path).lower()
            if filter_keyword_lower in filename:
                filtered_pdfs.append(pdf_path)
                continue
            
            full_text = extract_text_from_pdf(pdf_path)
            if full_text and filter_keyword_lower in full_text:
                filtered_pdfs.append(pdf_path)
        
        print(f"Found {len(filtered_pdfs)} matching reports to analyze.")
        target_pdfs = filtered_pdfs
    else:
        print("Analyzing all reports (no filter).")
        target_pdfs = all_pdfs

    for pdf_path in tqdm(target_pdfs, desc="Analyzing Reports", unit="pdf"):
        full_text = extract_text_from_pdf(pdf_path)
        if not full_text:
            continue
            
        for term in terms_to_search:
            negative_phrase = f"no evidence of {term}"
            if term in full_text and negative_phrase not in full_text:
                match_counts[term] += 1
                match_files[term].add(pdf_path)

    return match_files, match_counts

def main():
    """Main function to parse arguments and orchestrate the PDF search."""
    
    parser = argparse.ArgumentParser(description="Scan PDF reports for specific medical terms.")
    parser.add_argument('--scan-all', action='store_true', help='Scan all PDF reports without filtering by body part.')
    parser.add_argument('--scan', type=str, metavar='"SCAN TYPE"', help='Scan only for a specific report type (e.g., "CT abdomen").')
    
    args = parser.parse_args()

    if not args.scan_all and not args.scan:
        parser.error("No action requested. Please use --scan-all or --scan \"SCAN TYPE\".")
        return

    filter_keyword = args.scan if args.scan else None
    
    search_terms = [term.lower() for term in SEARCH_TERMS]
    
    # --- NEW FEATURE LOGIC: INDEXING ---
    all_pdf_paths = []
    if os.path.exists(INDEX_FILE):
        print(f"Loading file paths from existing index '{INDEX_FILE}'...")
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            all_pdf_paths = [line.strip() for line in f if line.strip()]
    else:
        print("No index file found. Creating one now (this may take a few minutes)...")
        folders_to_scan = [REPORTS_FOLDER, MAIN_FOLDER]
        all_pdf_paths = list(tqdm(stream_pdfs(folders_to_scan), desc="Indexing PDF files"))
        try:
            with open(INDEX_FILE, 'w', encoding='utf-8') as f:
                for path in all_pdf_paths:
                    f.write(path + '\n')
            print(f"Index file '{INDEX_FILE}' created successfully.")
        except Exception as e:
            print(f"Could not write index file: {e}")
    # --- END OF NEW FEATURE LOGIC ---

    if not all_pdf_paths:
        print("No PDF files found. Exiting.")
        return
    print(f"Discovery complete. Found {len(all_pdf_paths)} PDF files.\n")

    files_dict, counts = find_and_process_pdfs(
        all_pdf_paths, 
        search_terms, 
        filter_keyword
    )

    report_lines = ["--- Search Results ---"]
    report_lines.append(f"\n{'='*55}")
    if filter_keyword:
        report_lines.append(f"## Results for reports filtered by: '{filter_keyword}'")
    else:
        report_lines.append("## Results for all scanned reports")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")
    
    total_unique_files = set()
    for term, count in counts.items():
        report_lines.append(f"  - {term:<25}: {count} reports")
        total_unique_files.update(files_dict[term])
    
    report_lines.append(f"\n### Total Unique Reports in this Category: {len(total_unique_files)}")
    report_lines.append("--- File List ---")
    
    for term in search_terms:
        files = sorted(list(files_dict[term]))
        if files:
            report_lines.append(f"\n#### Files containing '{term}':")
            for file_path in files:
                report_lines.append(f"- {file_path}")
    
    report_lines.append("\n--- End of Report ---")

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        print(f"\nAnalysis complete. Report successfully saved to: {os.path.abspath(OUTPUT_FILE)}")
    except Exception as e:
        print(f"\nError: Could not write report to file. {e}")

if __name__ == "__main__":
    main()