import os
from pypdf import PdfReader
from tqdm import tqdm
import logging

# --- CONFIGURATION ---

# 1. Path to the folder with unmatched reports (e.g., folder/report.pdf)
REPORTS_FOLDER = r"C:\path\to\unmatched_reports"

# 2. Path to the main folder with patient subfolders (e.g., main_folder/patient/report.pdf)
MAIN_FOLDER = r"C:\path\to\matched_reports"

# 3. List of search terms.
SEARCH_TERMS = [
    "acute diverticulitis",
    "acute cholecystitis",
    "acute pancreas",
    "Appendicite"
]

# Suppress verbose logging from the PDF library to keep the output clean
logging.basicConfig(level=logging.WARNING)


def find_all_pdfs(folders_to_scan):
    """
    Scans all provided folders, including subdirectories, and yields the full path of every PDF file found.
    """
    pdf_files = []
    print("Finding all PDF files to scan...")
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            print(f"Warning: The folder '{folder}' does not exist and will be skipped.")
            continue
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
    print(f"Found a total of {len(pdf_files)} PDF files.")
    return pdf_files

def extract_text_from_pdf(pdf_path):
    """
    Reads all text from a PDF and returns it as a single lowercase string.
    Returns None if the file cannot be read.
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            # Combine text from all pages into one lower-case string for efficient searching
            return " ".join(page.extract_text().lower() for page in reader.pages if page.extract_text())
    except Exception as e:
        # Gracefully handle corrupted or unreadable PDFs
        print(f"\nCould not read or process file: {os.path.basename(pdf_path)}. Error: {e}")
        return None

def main():
    """Main function to orchestrate the PDF search and reporting."""
    
    # Automatically create the list of terms without "acute"
    terms_with_acute = [term.lower() for term in SEARCH_TERMS]
    terms_without_acute = [term.replace('acute ', '').lower() for term in terms_with_acute]
    terms_without_acute = list(set(terms_without_acute))
    
    # Gather all PDFs from both specified locations
    all_pdfs = find_all_pdfs([REPORTS_FOLDER, MAIN_FOLDER])
    
    if not all_pdfs:
        print("No PDFs found in the specified directories. Exiting.")
        return

    # Initialize lists to store the results
    exact_match_files = []
    partial_match_files = []

    # Process all PDFs with a progress bar
    for pdf_path in tqdm(all_pdfs, desc="Analyzing Reports", unit="pdf"):
        full_text = extract_text_from_pdf(pdf_path)
        
        if full_text:
            # --- LOGIC CHANGE IS HERE ---
            # The two checks are now independent. A file can be added to both lists.

            # Check 1: Does the PDF contain any of the original terms?
            if any(term in full_text for term in terms_with_acute):
                exact_match_files.append(pdf_path)
            
            # Check 2: Does the PDF contain any of the "without acute" terms?
            if any(term in full_text for term in terms_without_acute):
                partial_match_files.append(pdf_path)

    # --- Final Report ---
    print("\n\n--- Search Results ---")

    print("\n" + "="*55)
    print(f"## 1. List 1: Reports with original terms")
    print(f"## (e.g., 'acute diverticulitis', 'Appendicite')")
    print(f"## Found: {len(exact_match_files)} reports")
    print("="*55)
    if exact_match_files:
        for file_path in exact_match_files:
            print(f"- {file_path}")
    else:
        print("No reports found matching the original terms.")

    print("\n" + "="*55)
    print(f"## 2. List 2: Reports with terms excluding 'acute'")
    print(f"## (e.g., 'diverticulitis', 'Appendicite')")
    print(f"## NOTE: This list can include duplicates from List 1.")
    print(f"## Found: {len(partial_match_files)} reports")
    print("="*55)
    if partial_match_files:
        for file_path in partial_match_files:
            print(f"- {file_path}")
    else:
        print("No reports found matching the partial terms.")

    print("\n--- End of Report ---\n")

if __name__ == "__main__":
    main()