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
    "abscess",
    "acute appendicitis",
    "acute cholecystitis",
    "acute on chronic pancreatitis",
    "acute pancreatitis",
    "adrenal adenoma",
    "adrenal hyperplasia",
    "ascites",
    "atherosclerotic changes",
    "biliary sludge",
    "bowel obstruction",
    "bowel wall thickening",
    "bulky pancreas",
    "calculi",
    "cardiomegaly",
    "cholecystitis",
    "cholelithiasis",
    "cirrhosis",
    "colitis",
    "contracted gall bladder",
    "cystitis",
    "distended gall bladder",
    "divarication of recti",
    "diverticulitis",
    "diverticulosis",
    "emphysematous cholecystitis",
    "esophageal thickening",
    "fatty liver",
    "fibrocalcific changes",
    "gall bladder wall thickening",
    "hepatitis",
    "hepatic cyst",
    "hepatomegaly",
    "hepatosplenomegaly",
    "hernia",
    "hydronephrosis",
    "hydroureteronephrosis",
    "ileitis",
    "ileocolitis",
    "lesion",
    "lymphadenopathy",
    "necrosis",
    "pancreatitis",
    "pericholecystic fluid",
    "perinephric fat stranding",
    "pleural effusion",
    "pneumonia",
    "portal hypertension",
    "prostatomegaly",
    "pyelonephritis",
    "renal calculi",
    "renal cyst",
    "splenomegaly",
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

def find_and_process_pdfs(all_pdfs, search_terms, filter_keyword=None):
    """
    Finds and processes PDFs, applying positive match logic for each term.
    """
    print("Starting analysis... Press Ctrl+C to stop.")

    match_counts = {term: 0 for term in search_terms}
    match_files = {term: set() for term in search_terms}
    
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
            # Split the entire text into sentences once per PDF
            sentences = nltk.sent_tokenize(full_text)

            # Process the single search list
            for term in search_terms:
                term_found_positively = False
                for sentence in sentences:
                    if term in sentence:
                        # If the term is in the sentence, check for negations in the same sentence
                        if not any(neg in sentence for neg in ["no evidence of", "no sign of", "negative for"]):
                            term_found_positively = True
                            break  # A single positive mention is enough
                if term_found_positively:
                    match_counts[term] += 1
                    match_files[term].add(pdf_path)

    return match_files, match_counts

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
        filter_keyword
    )

    # --- Reporting ---
    report_lines = []
    report_lines.append("--- Search Results ---")
    
    # Report for the consolidated list
    report_lines.append(f"\n{'='*55}")
    report_lines.append("## 1. Search Results")
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