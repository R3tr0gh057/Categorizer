import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging

# --- CONFIGURATION ---
REPORTS_FOLDER = r"C:\path\to\unmatched_reports"
MAIN_FOLDER = r"C:\path\to\matched_reports"

SEARCH_TERMS = [
    "acute diverticulitis",
    "acute cholecystitis",
    "acute pancreas",
    "acute pancreatitis",
    "appendicite",
    "appendicitis"
]

OUTPUT_FILE = "search_report_post_correction.txt"


# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# --- FUNCTION MODIFIED FOR BETTER FEEDBACK ---
def get_pdf_paths(folders_to_scan):
    """
    Scans folders and subfolders to find all PDF paths, showing a progress bar during discovery.
    """
    pdf_paths = []
    print("Phase 1: Discovering PDF files...")
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            print(f"Warning: Folder not found, skipping: {folder}")
            continue
        # Using a simple loop with tqdm for immediate feedback on file discovery
        # This is a conceptual progress bar as os.walk discovery speed varies.
        print(f"Scanning folder: {folder}")
        for root, _, files in tqdm(os.walk(folder, topdown=True), desc="Scanning subdirectories", unit="dir"):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_paths.append(os.path.join(root, file))
    print(f"Discovery complete. Found {len(pdf_paths)} PDF files in total.")
    return pdf_paths

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF using PyMuPDF and returns it as a lowercase string."""
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text").lower() for page in doc)
    except Exception as e:
        logging.error(f"Failed to read or process {pdf_path}: {e}")
        return None

def find_and_process_pdfs(all_pdfs, terms_with_acute, terms_without_acute):
    """
    Processes a given list of PDFs, applying positive match logic for each term.
    """
    print("\nPhase 2: Analyzing report content...")
    
    exact_match_counts = {term: 0 for term in terms_with_acute}
    partial_match_counts = {term: 0 for term in terms_without_acute}
    
    exact_match_files = {term: set() for term in terms_with_acute}
    partial_match_files = {term: set() for term in terms_without_acute}
    
    for pdf_path in tqdm(all_pdfs, desc="Analyzing Reports", unit="pdf", mininterval=1.0):
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
    """Main function to orchestrate the PDF search and reporting."""
    terms_with_acute = sorted([term.lower() for term in SEARCH_TERMS])
    terms_without_acute = sorted(list(set([term.replace('acute ', '').lower() for term in terms_with_acute])))
    
    folders_to_scan = [REPORTS_FOLDER, MAIN_FOLDER]
    
    # Phase 1: Get all PDF paths with progress
    all_pdf_paths = get_pdf_paths(folders_to_scan)
    
    # Phase 2: Analyze the found PDFs
    exact_files_dict, partial_files_dict, exact_counts, partial_counts = find_and_process_pdfs(
        all_pdf_paths, 
        terms_with_acute, 
        terms_without_acute
    )

    # ... (The entire reporting section is unchanged) ...
    report_lines = []
    report_lines.append("--- Search Results ---")

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