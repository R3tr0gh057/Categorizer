import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import re # Added for sentence splitting
import argparse

# --- CONFIGURATION ---
# Folder with PDFs directly inside (no subfolders)
REPORTS_FOLDER = r"D:\DATA\Desktop\Reports"
# Folder with nested patient folders that contain PDFs
MAIN_FOLDER = r"E:\InnoWave_Data\filestore"

# Default search terms if none are specified via arguments
# (These will be converted to lowercase later)
SEARCH_TERMS = [
    "appendicitis",
    "acute appendicitis",
    "chronic appendicitis",
    "appendicitis with collection or abscess",
    "rupture appendicitis",
    "acute pancreatitis",
    "chronic pancreatitis",
    "Pancreatitis",
    "modified ctsi",
    "pancreatitis with collection",
]

# Default output/index filenames (can be overridden by arguments)
OUTPUT_FILE = "search_report_results_appendicitis_sentence_level.txt"
INDEX_FILE = "pdf_index.txt"

# --- NEW: Negative Keywords for Sentence-Level Check (lowercase) ---
# Consider expanding this list based on common radiological phrasing
NEGATIVE_KEYWORDS = [
    "no evidence", "not seen", "negative for", "ruled out", "unlikely",
    "absent", "without signs of", "is unremarkable", "no definite",
    "no significant", "no obvious", "no acute", "normal appendix",
    "appendix is normal", "no features of", "no sign of",
    "scan negative for", "no suspicion of", "scan does not show",
    "no imaging findings of", "no ct evidence of"
]

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
        # os.walk is efficient for traversing directories
        for root, _, files in os.walk(folder, topdown=True):
            for file in files:
                if file.lower().endswith('.pdf'):
                    yield os.path.join(root, file)

def extract_text_from_pdf(pdf_path):
    """Reads all text from a PDF and returns it as a single lowercase string."""
    try:
        # Use a context manager to ensure the file is closed properly
        with fitz.open(pdf_path) as doc:
            # Efficiently join text from all pages
            return " ".join(page.get_text("text", sort=True).lower() for page in doc) # Added sort=True for better reading order
    except Exception as e:
        # Log errors instead of just printing to tqdm to avoid cluttering progress bar
        logging.error(f"Skipping corrupted/unreadable file: {os.path.basename(pdf_path)} ({e})")
        # Optional: Log the full path for easier debugging: logging.error(f"Full path: {pdf_path}")
        return None

def find_and_process_pdfs(all_pdfs, terms_to_search, filter_keyword=None):
    """
    Finds and processes PDFs using sentence-level analysis.
    Optionally filters PDFs by a keyword in the filename or content.
    Returns:
        tuple: (match_files, match_counts, total_unique_count)
    """
    print("Starting analysis (sentence-level)... Press Ctrl+C to stop.")

    match_counts = {term: 0 for term in terms_to_search}
    match_files = {term: set() for term in terms_to_search}

    # --- Filtering Logic ---
    if filter_keyword:
        print(f"Filtering for reports containing '{filter_keyword}'...")
        filtered_pdfs = []
        filter_keyword_lower = filter_keyword.lower()

        # Optimization: Filter filenames first
        pdf_paths_to_check_content = []
        for pdf_path in tqdm(all_pdfs, desc="Filtering PDF filenames", unit="pdf", leave=False):
             filename = os.path.basename(pdf_path).lower()
             if filter_keyword_lower in filename:
                 filtered_pdfs.append(pdf_path)
             else:
                 pdf_paths_to_check_content.append(pdf_path)

        # Now check content only for those not matched by filename
        for pdf_path in tqdm(pdf_paths_to_check_content, desc="Filtering PDF content", unit="pdf", leave=False):
            full_text = extract_text_from_pdf(pdf_path)
            # Check if text extraction was successful and keyword is present
            if full_text and filter_keyword_lower in full_text:
                filtered_pdfs.append(pdf_path)

        print(f"Found {len(filtered_pdfs)} reports matching filter to analyze.")
        target_pdfs = filtered_pdfs # Analyze only the filtered list
    else:
        print("Analyzing all indexed reports (no filter).")
        target_pdfs = all_pdfs # Analyze the full list

    # --- Analysis Loop with Sentence Logic ---
    for pdf_path in tqdm(target_pdfs, desc="Analyzing Reports", unit="pdf", leave=True):
        full_text = extract_text_from_pdf(pdf_path)
        if not full_text:
            continue # Skip if text extraction failed

        # Split into sentences using regex (handles '.', '?', '!') followed by whitespace
        # This is more robust than just splitting by ". "
        sentences = re.split(r'[.?!]\s+', full_text)
        # Remove any empty strings resulting from the split and surrounding whitespace
        sentences = [s.strip() for s in sentences if s.strip()]

        # Iterate through each search term for the current PDF
        for term in terms_to_search:
            term_found_positively = False # Flag to check if term is found positively in *any* sentence
            for sentence in sentences:
                # 1. Check if the primary term is in the sentence
                if term in sentence:
                    # 2. Check if *any* negative keyword is ALSO in the SAME sentence
                    is_negated = any(neg_kw in sentence for neg_kw in NEGATIVE_KEYWORDS)

                    # 3. If term is present AND no negative keyword is present in the sentence, it's a positive match
                    if not is_negated:
                        term_found_positively = True
                        break # Found a positive sentence for this term, no need to check other sentences in this PDF for this term

            # If the term was found positively in at least one sentence of this PDF
            if term_found_positively:
                 # Check if this PDF path is already in the set for this term to avoid double counting
                 # (though break above should prevent this for a single PDF run)
                if pdf_path not in match_files[term]:
                    match_counts[term] += 1
                    match_files[term].add(pdf_path)
                 # If using pdf_matched_terms set from thought process:
                 # pdf_matched_terms.add(term) # useful if we needed unique PDF count per PDF later

    # Calculate total unique files based on the collected sets across all terms
    total_unique_files_overall = set()
    for term in terms_to_search:
        total_unique_files_overall.update(match_files[term])

    # Return the dictionary of files per term, counts per term, and the overall unique count
    return match_files, match_counts, len(total_unique_files_overall)


def main():
    """Main function to parse arguments and orchestrate the PDF search."""

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Scan PDF reports for specific medical terms using sentence-level analysis.")
    parser.add_argument('--scan-all', action='store_true', help='Scan all indexed PDF reports without filtering by body part.')
    parser.add_argument('--scan', type=str, metavar='"SCAN TYPE"', help='Scan only for reports matching a specific filter keyword (e.g., "CT abdomen"). Checks filename and content.')
    parser.add_argument('-o', '--output', type=str, default=OUTPUT_FILE, help=f'Specify the output report file name (default: {OUTPUT_FILE}).')
    parser.add_argument('-i', '--index', type=str, default=INDEX_FILE, help=f'Specify the PDF index file name (default: {INDEX_FILE}).')

    args = parser.parse_args()

    # Ensure at least one scan action is requested
    if not args.scan_all and not args.scan:
        parser.error("No action requested. Please use --scan-all or --scan \"SCAN TYPE\".")
        return # Exit if no action

    filter_keyword = args.scan if args.scan else None
    output_filename = args.output
    index_filename = args.index

    # Ensure all search terms are lowercase for consistent matching
    search_terms = [term.lower() for term in SEARCH_TERMS]

    # --- PDF Indexing/Loading ---
    all_pdf_paths = []
    if os.path.exists(index_filename):
        print(f"Loading file paths from existing index '{index_filename}'...")
        try:
            with open(index_filename, 'r', encoding='utf-8') as f:
                # Read paths, strip whitespace, ignore empty lines
                all_pdf_paths = [line.strip() for line in f if line.strip()]
            if not all_pdf_paths:
                 print(f"Warning: Index file '{index_filename}' is empty. Re-indexing.")
            else:
                 print(f"Loaded {len(all_pdf_paths)} paths from index.")
        except Exception as e:
            print(f"Error reading index file '{index_filename}': {e}. Re-indexing.")
            all_pdf_paths = [] # Force re-indexing on error

    # If index didn't exist, was empty, or failed to load, create it
    if not all_pdf_paths:
        print("Indexing PDF files (this may take a few minutes)...")
        # Define folders to scan here (ensure REPORTS_FOLDER and MAIN_FOLDER are accessible)
        folders_to_scan = [REPORTS_FOLDER, MAIN_FOLDER]
        # Use the generator directly with list() to build the list; tqdm provides progress
        all_pdf_paths = list(tqdm(stream_pdfs(folders_to_scan), desc="Indexing PDF files"))

        if all_pdf_paths: # Only write index if PDFs were found
            try:
                with open(index_filename, 'w', encoding='utf-8') as f:
                    for path in all_pdf_paths:
                        f.write(path + '\n') # Write each path on a new line
                print(f"Index file '{index_filename}' created successfully with {len(all_pdf_paths)} paths.")
            except Exception as e:
                print(f"Error: Could not write index file '{index_filename}': {e}")
        else:
             print("Indexing found no PDF files in the specified folders. Exiting.")
             return # Exit if no PDFs found during indexing
    # --- End of Indexing Logic ---

    # Double-check if we have paths before proceeding
    if not all_pdf_paths:
        print("No PDF file paths available to process. Exiting.")
        return
    print(f"Proceeding with analysis on {len(all_pdf_paths)} indexed PDF files.\n")

    # --- Perform Analysis ---
    # Call the modified function which now returns the total unique count directly
    files_dict, counts, total_unique_count = find_and_process_pdfs(
        all_pdf_paths,
        search_terms,
        filter_keyword
    )

    # --- Report Generation ---
    report_lines = ["--- Search Results (Sentence-Level Analysis) ---"] # Updated report title
    report_lines.append(f"\n{'='*55}")
    if filter_keyword:
        report_lines.append(f"## Results for reports filtered by: '{filter_keyword}'")
    else:
        report_lines.append("## Results for all scanned reports")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")

    # Add counts for each term
    for term, count in sorted(counts.items()): # Sort terms alphabetically in report
        report_lines.append(f"  - {term:<25}: {count} reports")

    # Add the total unique count returned by the function
    report_lines.append(f"\n### Total Unique Reports in this Category: {total_unique_count}")
    report_lines.append("--- File List ---")

    # Add file lists for each term
    for term in sorted(search_terms): # Sort terms alphabetically here too
        # Use .get() to safely access the set, defaulting to an empty set if term has no matches
        files = sorted(list(files_dict.get(term, set())))
        if files: # Only add section if files were found for this term
            report_lines.append(f"\n#### Files containing '{term}':")
            for file_path in files:
                report_lines.append(f"- {file_path}") # List each file path

    report_lines.append("\n--- End of Report ---")

    # --- Save Report ---
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines)) # Write all collected lines to the file
        print(f"\nAnalysis complete. Report successfully saved to: {os.path.abspath(output_filename)}")
    except Exception as e:
        # Provide error message if saving fails
        print(f"\nError: Could not write report to file '{output_filename}'. {e}")

# Standard Python entry point check
if __name__ == "__main__":
    main()