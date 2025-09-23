import os
from pypdf import PdfReader
from tqdm import tqdm
import logging

# --- CONFIGURATION ---
# IMPORTANT: Update these paths to match your system
# D:\OLD REPORTS\2025 JAN-JUL
# D:\OLD REPORTS\2024
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

OUTPUT_FILE = "search_report_lucknow.txt"


# --- SCRIPT ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def stream_pdfs(folders_to_scan):
    """A generator that finds and 'yields' one PDF path at a time."""
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            print(f"Warning: Folder not found, skipping: {folder}")
            continue
        for root, _, files in os.walk(folder, topdown=True):
            for file in files:
                if file.lower().endswith('.pdf'):
                    yield os.path.join(root, file)

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF and returns it as a single lowercase string."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            # Ensure text extraction is not None before joining
            page_texts = [page.extract_text().lower() for page in reader.pages if page.extract_text()]
            return " ".join(page_texts)
    except Exception as e:
        logging.error(f"Failed to read or process {pdf_path}: {e}")
        return None

def find_and_process_pdfs(folders_to_scan, terms_with_acute, terms_without_acute):
    """
    Finds and processes PDFs, applying positive match logic for each term.
    """
    print("Starting analysis... Press Ctrl+C to stop.")
    
    # Dictionaries to hold counts and file paths for each specific term
    exact_match_counts = {term: 0 for term in terms_with_acute}
    partial_match_counts = {term: 0 for term in terms_without_acute}
    
    exact_match_files = {term: set() for term in terms_with_acute}
    partial_match_files = {term: set() for term in terms_without_acute}
    
    # Use a generator to avoid loading all paths into memory at once
    pdf_generator = stream_pdfs(folders_to_scan)
    
    # Create a list from the generator to use with tqdm for a total count
    all_pdfs = list(pdf_generator)
    
    for pdf_path in tqdm(all_pdfs, desc="Analyzing Reports", unit="pdf", mininterval=1.0):
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            # --- Positive Match Logic for List 1 (Original Terms) ---
            for term in terms_with_acute:
                negative_phrase = f"no evidence of {term}"
                if term in full_text and negative_phrase not in full_text:
                    exact_match_counts[term] += 1
                    exact_match_files[term].add(pdf_path)
            
            # --- Positive Match Logic for List 2 (Terms without 'acute') ---
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
    
    exact_files_dict, partial_files_dict, exact_counts, partial_counts = find_and_process_pdfs(
        [REPORTS_FOLDER, MAIN_FOLDER], 
        terms_with_acute, 
        terms_without_acute
    )

    report_lines = []
    report_lines.append("--- Search Results ---")

    # --- Report for List 1 ---
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
    
    # List files for each term individually
    for term in terms_with_acute:
        files = sorted(list(exact_files_dict[term]))
        if files:
            report_lines.append(f"\n#### Files containing '{term}':")
            for file_path in files:
                report_lines.append(f"- {file_path}")

    # --- Report for List 2 ---
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
    
    # List files for each term individually
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