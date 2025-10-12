import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import argparse # Added for command-line arguments
import nltk # Added for sentence splitting

# --- CONFIGURATION ---
# These folders will be scanned
FOLDERS_TO_SCAN = [
    r"D:\OLD REPORTS\2024",
    r"D:\OLD REPORTS\2025 JAN-JUL"
]

# Default search terms
SEARCH_TERMS = [
    "Ca lung",
    "Neoplastic etiology",
    "Metastasis",
    "Carcinoma lung",
    "Bronchogenic carcinoma",
    "Alveolar cell carcinoma",
]

OUTPUT_FILE = "search_report_lucknow_updated.txt"


# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# nltk initialization
try:
    nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError:
    print("First-time setup: Downloading 'punkt' tokenizer for sentence analysis...")
    nltk.download('punkt')
    print("Download complete.")

def stream_pdfs(folders_to_scan):
    """
    A generator that finds PDFs directly inside the specified folders.
    This version does NOT look into subdirectories.
    """
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            print(f"Warning: Folder not found, skipping: {folder}")
            continue
        try:
            for filename in os.listdir(folder):
                if filename.lower().endswith('.pdf'):
                    yield os.path.join(folder, filename)
        except Exception as e:
            logging.error(f"Could not read files in folder {folder}: {e}")

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF using the much faster PyMuPDF library."""
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text").lower() for page in doc)
    except Exception as e:
        logging.error(f"Failed to read or process {pdf_path}: {e}")
        return None

# --- MODIFIED FUNCTION ---
def find_and_process_pdfs(all_pdfs, search_terms, body_part_filters=None, scan_type_filters=None):
    """
    Finds and processes PDFs, applying positive match logic for each term.
    """
    print("Starting analysis... Press Ctrl+C to stop.")

    match_counts = {term: 0 for term in search_terms}
    match_files = {term: set() for term in search_terms}
    
    # Filter PDFs first if any filters are provided
    if body_part_filters or scan_type_filters:
        print(f"Filtering for reports...")
        filtered_pdfs = []
        
        body_filters_lower = [f.lower() for f in body_part_filters] if body_part_filters else []
        type_filters_lower = [f.lower() for f in scan_type_filters] if scan_type_filters else []

        for pdf_path in tqdm(all_pdfs, desc="Filtering PDFs", unit="pdf"):
            filename = os.path.basename(pdf_path).lower()
            full_text = None

            # 1. Check for body part (OR logic)
            body_part_match = False
            if not body_filters_lower:
                body_part_match = True
            else:
                if any(part in filename for part in body_filters_lower):
                    body_part_match = True
                else:
                    full_text = extract_text_from_pdf(pdf_path)
                    if full_text and any(part in full_text for part in body_filters_lower):
                        body_part_match = True

            if not body_part_match:
                continue

            # 2. Check for scan type (AND logic)
            scan_type_match = False
            if not type_filters_lower:
                scan_type_match = True
            else:
                all_types_found = True
                for scan_type in type_filters_lower:
                    if scan_type in filename:
                        continue
                    
                    if not full_text:
                        full_text = extract_text_from_pdf(pdf_path)
                    
                    if not full_text or scan_type not in full_text:
                        all_types_found = False
                        break
                if all_types_found:
                    scan_type_match = True
            
            if body_part_match and scan_type_match:
                filtered_pdfs.append(pdf_path)
        
        print(f"Found {len(filtered_pdfs)} matching reports to analyze.")
        target_pdfs = filtered_pdfs
    else:
        print("Analyzing all reports (no filter).")
        target_pdfs = all_pdfs
    
    for pdf_path in tqdm(target_pdfs, desc="Analyzing Reports", unit="pdf", mininterval=1.0):
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            sentences = nltk.sent_tokenize(full_text)
            for term in search_terms:
                term_found_positively = False
                for sentence in sentences:
                    if term in sentence:
                        if not any(neg in sentence for neg in ["no evidence of", "no sign of", "negative for"]):
                            term_found_positively = True
                            break
                if term_found_positively:
                    match_counts[term] += 1
                    match_files[term].add(pdf_path)

    return match_files, match_counts

def main():
    """Main function to parse arguments and orchestrate the PDF search."""

    # --- MODIFIED ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Scan PDF reports for specific medical terms. Run with no arguments to scan all reports.")
    parser.add_argument('--scan', type=str, nargs='+', metavar='BODY_PART', help='Scan for specific body parts (e.g., "abdomen" "chest"). At least one must be present.')
    parser.add_argument('--type', type=str, nargs='+', metavar='SCAN_TYPE', help='Also filter by scan types (e.g., "cect" "contrast"). All types must be present.')
    
    args = parser.parse_args()
    
    # --- Main Script Logic ---
    search_terms = sorted([term.lower() for term in SEARCH_TERMS])
    
    print("Discovering PDF files...")
    all_pdf_paths = list(stream_pdfs(FOLDERS_TO_SCAN))
    if not all_pdf_paths:
        print("No PDF files found. Exiting.")
        return
    print(f"Discovery complete. Found {len(all_pdf_paths)} PDF files.\n")
    
    files_dict, counts = find_and_process_pdfs(
        all_pdf_paths, 
        search_terms,
        body_part_filters=args.scan,
        scan_type_filters=args.type
    )

    # --- Reporting ---
    report_lines = []
    report_lines.append("--- Search Results ---")
    
    report_lines.append(f"\n{'='*55}")
    if args.scan or args.type:
        scan_info = f"Scan Body Parts: {args.scan}" if args.scan else "Any"
        type_info = f"Scan Types: {args.type}" if args.type else "Any"
        report_lines.append(f"## Results for reports filtered by: {scan_info} | {type_info}")
    else:
        report_lines.append("## Results for all scanned reports (no filters applied)")
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