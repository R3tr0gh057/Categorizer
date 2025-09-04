import os
from pypdf import PdfReader
from tqdm import tqdm
import logging

# --- CONFIGURATION ---
REPORTS_FOLDER = r"C:\path\to\unmatched_reports"
MAIN_FOLDER = r"C:\path\to\matched_reports"
SEARCH_TERMS = [
    "acute diverticulitis",
    "acute cholecystitis",
    "acute pancreas",
    "Appendicite"
]

# NEW: Name for the output report file.
# This file will be saved in the same directory where you run the script.
OUTPUT_FILE = "search_report.txt"


logging.basicConfig(level=logging.WARNING)


def find_and_process_pdfs(folders_to_scan, terms_with_acute, terms_without_acute):
    """
    Finds and processes each PDF one by one, yielding individual counts for each search term.
    """
    print("Starting analysis... Press Ctrl+C to stop.")
    
    exact_match_counts = {term: 0 for term in terms_with_acute}
    partial_match_counts = {term: 0 for term in terms_without_acute}
    
    exact_match_files = set()
    partial_match_files = set()
    
    pdf_generator = stream_pdfs(folders_to_scan)
    
    for pdf_path in tqdm(pdf_generator, desc="Analyzing Reports", unit="pdf", mininterval=1.0):
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            for term in terms_with_acute:
                if term in full_text:
                    exact_match_counts[term] += 1
                    exact_match_files.add(pdf_path)
            
            for term in terms_without_acute:
                if term in full_text:
                    partial_match_counts[term] += 1
                    partial_match_files.add(pdf_path)

    return list(exact_match_files), list(partial_match_files), exact_match_counts, partial_match_counts

def stream_pdfs(folders_to_scan):
    """A generator that finds and 'yields' one PDF path at a time."""
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
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
            return " ".join(page.extract_text().lower() for page in reader.pages if page.extract_text())
    except Exception:
        return None

def main():
    """Main function to orchestrate the PDF search and reporting."""
    terms_with_acute = [term.lower() for term in SEARCH_TERMS]
    terms_without_acute = sorted(list(set([term.replace('acute ', '').lower() for term in terms_with_acute])))
    
    exact_files, partial_files, exact_counts, partial_counts = find_and_process_pdfs(
        [REPORTS_FOLDER, MAIN_FOLDER], 
        terms_with_acute, 
        terms_without_acute
    )

    # --- NEW: Build the report as a list of strings ---
    report_lines = []
    report_lines.append("--- Search Results ---")

    # Report for List 1
    report_lines.append(f"\n{'='*55}")
    report_lines.append(f"## 1. List 1: Reports with original terms")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")
    for term, count in exact_counts.items():
        report_lines.append(f"  - {term:<25}: {count} reports")
    report_lines.append(f"\n### Total Unique Reports in this Category: {len(exact_files)}")
    report_lines.append("--- File List ---")
    if exact_files:
        for file_path in exact_files:
            report_lines.append(f"- {file_path}")
    else:
        report_lines.append("No reports found.")

    # Report for List 2
    report_lines.append(f"\n{'='*55}")
    report_lines.append(f"## 2. List 2: Reports with terms excluding 'acute'")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")
    for term, count in partial_counts.items():
        report_lines.append(f"  - {term:<25}: {count} reports")
    report_lines.append(f"\n### Total Unique Reports in this Category: {len(partial_files)}")
    report_lines.append("--- File List ---")
    if partial_files:
        for file_path in partial_files:
            report_lines.append(f"- {file_path}")
    else:
        report_lines.append("No reports found.")
    
    report_lines.append("\n--- End of Report ---")

    # --- NEW: Write the entire report to the output file ---
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        print(f"\nAnalysis complete. Report successfully saved to: {os.path.abspath(OUTPUT_FILE)}")
    except Exception as e:
        print(f"\nError: Could not write report to file. {e}")


if __name__ == "__main__":
    main()