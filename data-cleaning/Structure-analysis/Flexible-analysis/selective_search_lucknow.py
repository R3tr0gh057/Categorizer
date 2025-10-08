import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import argparse # Added for command-line arguments

# --- CONFIGURATION ---
# These folders will be scanned
FOLDERS_TO_SCAN = [
    r"D:\OLD REPORTS\2024",
    r"D:\OLD REPORTS\2025 JAN-JUL"
]

# Default search terms
SEARCH_TERMS = [
    "acute diverticulitis",
    "acute cholecystitis",
    "acute pancreas",
    "acute pancreatitis",
    "acute appendicitis",
    "cect chest",
    "hrct chest", 
    "Neoplastic etiology", 
    "ca lung", 
    "carcinoma lung", 
    "metastasis lungs", 
    "cancer hospital", 
    "Rml hospital", 
    "mitotic pathology",
    "etiology" 
]

OUTPUT_FILE = "search_report_lucknow_updated.txt"


# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

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

def find_and_process_pdfs(all_pdfs, terms_with_acute, terms_without_acute, filter_keyword=None):
    """
    Finds and processes PDFs, applying positive match logic for each term.
    """
    print("Starting analysis... Press Ctrl+C to stop.")

    exact_match_counts = {term: 0 for term in terms_with_acute}
    partial_match_counts = {term: 0 for term in terms_without_acute}
    exact_match_files = {term: set() for term in terms_with_acute}
    partial_match_files = {term: set() for term in terms_without_acute}
    
    # Filter PDFs first if a keyword is provided
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
    
    for pdf_path in tqdm(target_pdfs, desc="Analyzing Reports", unit="pdf", mininterval=1.0):
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            for term in terms_with_acute:
                negative_phrase = f"no evidence of {term}"
                if term in full_text and negative_phrase not in full_text:
                    exact_match_counts[term] += 1
                    exact_match_files[term].add(pdf_path)
            
            for term in terms_without_acute:
                negative_phrase = f"no evidence of {term}"
                if term in full_text and negative_phrase not in full_text:
                    partial_match_counts[term] += 1
                    partial_match_files[term].add(pdf_path)

    return exact_match_files, partial_match_files, exact_match_counts, partial_match_counts

def main():
    """Main function to parse arguments and orchestrate the PDF search."""

    # --- Command-Line Argument Parsing ---
    parser = argparse.ArgumentParser(description="Scan PDF reports for specific medical terms.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--scan-all', action='store_true', help='Scan all PDF reports without filtering by body part.')
    group.add_argument('--scan', type=str, metavar='"SCAN TYPE"', help='Scan only for a specific report type (e.g., "CT abdomen").')
    
    args = parser.parse_args()
    
    filter_keyword = args.scan if args.scan else None

    # --- Main Script Logic ---
    terms_with_acute = sorted([term.lower() for term in SEARCH_TERMS])
    terms_without_acute = sorted(list(set([term.replace('acute ', '').lower() for term in terms_with_acute])))
    
    print("Discovering PDF files...")
    all_pdf_paths = list(stream_pdfs(FOLDERS_TO_SCAN))
    if not all_pdf_paths:
        print("No PDF files found. Exiting.")
        return
    print(f"Discovery complete. Found {len(all_pdf_paths)} PDF files.\n")
    
    exact_files_dict, partial_files_dict, exact_counts, partial_counts = find_and_process_pdfs(
        all_pdf_paths, 
        terms_with_acute, 
        terms_without_acute,
        filter_keyword
    )

    # --- Reporting ---
    report_lines = ["--- Search Results ---"]
    
    # Report for List 1
    report_lines.append(f"\n{'='*55}")
    report_lines.append("## 1. List 1: Reports with original terms")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")
    total_exact_files = set()
    for term, count in exact_counts.items():
        report_lines.append(f"  - {term:<25}: {count} reports")
        total_exact_files.update(exact_files_dict[term])
    
    report_lines.append(f"\n### Total Unique Reports in this Category: {len(total_exact_files)}")
    report_lines.append("--- File List ---")
    
    for term in terms_with_acute:
        files = sorted(list(exact_files_dict[term]))
        if files:
            report_lines.append(f"\n#### Files containing '{term}':")
            for file_path in files:
                report_lines.append(f"- {file_path}")

    # Report for List 2
    report_lines.append(f"\n{'='*55}")
    report_lines.append("## 2. List 2: Reports with terms excluding 'acute'")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")
    total_partial_files = set()
    for term, count in partial_counts.items():
        report_lines.append(f"  - {term:<25}: {count} reports")
        total_partial_files.update(partial_files_dict[term])
        
    report_lines.append(f"\n### Total Unique Reports in this Category: {len(total_partial_files)}")
    report_lines.append("--- File List ---")
    
    for term in terms_without_acute:
        files = sorted(list(partial_files_dict[term]))
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