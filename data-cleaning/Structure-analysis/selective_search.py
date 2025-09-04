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

logging.basicConfig(level=logging.WARNING)


def find_all_pdfs(folders_to_scan):
    """
    Scans all provided folders, including subdirectories, and returns a list of all PDF file paths.
    This version includes a real-time progress indicator for the scanning process.
    """
    pdf_files = []
    print("Finding all PDF files to scan... (This may take a while for large directories)")
    dir_count = 0
    
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            print(f"\nWarning: The folder '{folder}' does not exist and will be skipped.")
            continue
        try:
            for root, _, files in os.walk(folder, topdown=True):
                dir_count += 1
                # --- NEW: Real-time progress update ---
                # This prints the progress on a single line that constantly updates.
                # It updates every 100 directories to avoid slowing down the script.
                if dir_count % 100 == 0:
                    # Truncate the path display to keep the line clean
                    display_path = (root if len(root) < 70 else "..." + root[-67:])
                    print(f"\rScanned {dir_count} directories | Found {len(pdf_files)} PDFs | Current: {display_path}", end="")

                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_files.append(os.path.join(root, file))
        except OSError as e:
            print(f"\nError scanning a subdirectory in '{folder}': {e}")
            
    # --- NEW: Clear the progress line with a final message ---
    final_message = f"Scan complete. Found a total of {len(pdf_files)} PDF files."
    # Add padding to overwrite the previous line completely
    print(f"\r{final_message:<120}") 
    return pdf_files

def extract_text_from_pdf(pdf_path):
    """
    Reads all text from a PDF and returns it as a single lowercase string.
    Returns None if the file cannot be read.
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            return " ".join(page.extract_text().lower() for page in reader.pages if page.extract_text())
    except Exception:
        # Simplified error handling for this part
        return None

def main():
    """Main function to orchestrate the PDF search and reporting."""
    terms_with_acute = [term.lower() for term in SEARCH_TERMS]
    terms_without_acute = list(set([term.replace('acute ', '').lower() for term in terms_with_acute]))
    
    all_pdfs = find_all_pdfs([REPORTS_FOLDER, MAIN_FOLDER])
    
    if not all_pdfs:
        print("No PDFs found to analyze. Exiting.")
        return

    exact_match_files, partial_match_files = [], []

    for pdf_path in tqdm(all_pdfs, desc="Analyzing Reports", unit="pdf"):
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            if any(term in full_text for term in terms_with_acute):
                exact_match_files.append(pdf_path)
            if any(term in full_text for term in terms_without_acute):
                partial_match_files.append(pdf_path)

    print("\n\n--- Search Results ---")
    print(f"\n{'='*55}\n## 1. List 1: Reports with original terms\n## Found: {len(exact_match_files)} reports\n{'='*55}")
    for file_path in (exact_match_files or ["No reports found matching the original terms."]):
        print(f"- {file_path}")
    print(f"\n{'='*55}\n## 2. List 2: Reports with terms excluding 'acute'\n## NOTE: This list can include duplicates from List 1.\n## Found: {len(partial_match_files)} reports\n{'='*55}")
    for file_path in (partial_match_files or ["No reports found matching the partial terms."]):
        print(f"- {file_path}")
    print("\n--- End of Report ---\n")

if __name__ == "__main__":
    main()