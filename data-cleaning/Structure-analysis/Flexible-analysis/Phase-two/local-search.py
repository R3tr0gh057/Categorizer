import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import re # Added for sentence splitting
import argparse
import sys # Import sys to exit on error

# --- CONFIGURATION ---
# Default folder with PDFs directly inside (used if --use-custom-index is NOT provided)
DEFAULT_PDF_SOURCE_FOLDER = r"C:\Users\dedse\Downloads\fwdctreports" # CHANGE THIS if you have a different default

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
OUTPUT_FILE = "second-new-reports-iteration-no-filter.txt"
# Default index file used when *not* using a custom index
DEFAULT_INDEX_FILE = "new-reports-index.txt"

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

def list_pdfs_in_folder(folder_path):
    """
    Finds and yields PDF paths directly within the specified folder.
    Does NOT search subdirectories.
    """
    if not os.path.isdir(folder_path):
        tqdm.write(f"Error: Source folder not found: {folder_path}")
        return # Stop if folder doesn't exist

    try:
        for filename in os.listdir(folder_path):
            if filename.lower().endswith('.pdf'):
                yield os.path.join(folder_path, filename)
    except Exception as e:
        tqdm.write(f"Error listing files in folder {folder_path}: {e}")


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
    # Apply filtering even when using a custom index
    if filter_keyword:
        print(f"Filtering the provided list for reports containing '{filter_keyword}'...")
        filtered_pdfs = []
        filter_keyword_lower = filter_keyword.lower()

        # Check filenames first from the provided list
        pdf_paths_to_check_content = []
        for pdf_path in tqdm(all_pdfs, desc="Filtering PDF filenames", unit="pdf", leave=False):
             # Ensure path exists before checking basename (important for custom index)
             if not os.path.exists(pdf_path):
                 tqdm.write(f"Warning: File not found in custom index, skipping: {pdf_path}")
                 continue
             filename = os.path.basename(pdf_path).lower()
             if filter_keyword_lower in filename:
                 filtered_pdfs.append(pdf_path)
             else:
                 pdf_paths_to_check_content.append(pdf_path)

        # Now check content for those not matched by filename
        for pdf_path in tqdm(pdf_paths_to_check_content, desc="Filtering PDF content", unit="pdf", leave=False):
            # Path existence already checked in filename loop
            full_text = extract_text_from_pdf(pdf_path)
            # Check if text extraction was successful and keyword is present
            if full_text and filter_keyword_lower in full_text:
                filtered_pdfs.append(pdf_path)

        print(f"Found {len(filtered_pdfs)} reports from the list matching filter to analyze.")
        target_pdfs = filtered_pdfs # Analyze only the filtered list
    else:
        print("Analyzing all reports provided in the list (no filter).")
        target_pdfs = all_pdfs # Analyze the full list provided

    # --- Analysis Loop with Sentence Logic ---
    for pdf_path in tqdm(target_pdfs, desc="Analyzing Reports", unit="pdf", leave=True):
        # Check path existence again in case filtering was skipped but custom index has bad paths
        if not os.path.exists(pdf_path):
             tqdm.write(f"Warning: File not found during analysis, skipping: {pdf_path}")
             continue

        full_text = extract_text_from_pdf(pdf_path)
        if not full_text:
            continue # Skip if text extraction failed

        # Split into sentences using regex (handles '.', '?', '!') followed by whitespace
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
                        break # Found a positive sentence for this term, no need to check other sentences

            # If the term was found positively in at least one sentence of this PDF
            if term_found_positively:
                if pdf_path not in match_files[term]:
                    match_counts[term] += 1
                    match_files[term].add(pdf_path)

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
    # Input source arguments (mutually exclusive group recommended but complex, simpler check below)
    parser.add_argument('--folder', type=str, default=DEFAULT_PDF_SOURCE_FOLDER, help=f'Specify the folder containing PDF reports to index/scan (default: {DEFAULT_PDF_SOURCE_FOLDER}). Used if --use-custom-index is NOT provided.')
    parser.add_argument('--use-custom-index', type=str, metavar='FILEPATH', help='Specify a text file containing a list of PDF paths (one per line) to process instead of scanning a folder.')

    # Filtering and Output arguments
    parser.add_argument('--scan-all', action='store_true', help='Scan all indexed/provided PDF reports without filtering by keyword.')
    parser.add_argument('--scan', type=str, metavar='"KEYWORD"', help='Scan only for reports matching a specific filter keyword (e.g., "abdomen"). Checks filename and content.')
    parser.add_argument('-o', '--output', type=str, default=OUTPUT_FILE, help=f'Specify the output report file name (default: {OUTPUT_FILE}).')
    parser.add_argument('-i', '--index', type=str, default=DEFAULT_INDEX_FILE, help=f'Specify the PDF index file name for folder scanning (default: {DEFAULT_INDEX_FILE}). Ignored if --use-custom-index is used.')

    args = parser.parse_args()

    # --- Determine PDF Source ---
    all_pdf_paths = []
    pdf_source_description = "" # For reporting

    if args.use_custom_index:
        # --- Use Custom Index File ---
        custom_index_path = args.use_custom_index
        pdf_source_description = f"custom index file '{custom_index_path}'"
        print(f"Using custom index file: {custom_index_path}")
        if not os.path.exists(custom_index_path):
            print(f"Error: Custom index file not found: {custom_index_path}")
            sys.exit(1) # Exit if custom index doesn't exist

        try:
            with open(custom_index_path, 'r', encoding='utf-8') as f:
                # Read paths, strip whitespace, ignore empty lines
                all_pdf_paths = [line.strip() for line in f if line.strip()]
            if not all_pdf_paths:
                print(f"Warning: Custom index file '{custom_index_path}' is empty. No files to process.")
                return # Exit if custom index is empty
            print(f"Loaded {len(all_pdf_paths)} paths from custom index.")
        except Exception as e:
            print(f"Error reading custom index file '{custom_index_path}': {e}")
            sys.exit(1) # Exit on read error

        # When using custom index, --folder and -i are ignored for input finding
        pdf_source_folder = None # Not relevant for indexing
        index_filename = None # Not relevant for indexing

    else:
        # --- Use Folder Scanning and Managed Index ---
        pdf_source_folder = args.folder
        index_filename = args.index # Use the specified or default index name
        pdf_source_description = f"folder '{pdf_source_folder}' (using index '{index_filename}')"
        print(f"Using folder scanning for source: {pdf_source_folder}")
        print(f"Managed index file: {index_filename}")

        # Check if index file exists AND belongs to the *current* target folder
        index_needs_update = True # Assume update needed
        if os.path.exists(index_filename):
            print(f"Checking existing index '{index_filename}'...")
            try:
                with open(index_filename, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip() # Read the stored folder path
                    if first_line == pdf_source_folder:
                        print(f"Index seems up-to-date for folder: {pdf_source_folder}. Loading paths...")
                        all_pdf_paths = [line.strip() for line in f if line.strip()]
                        if all_pdf_paths:
                            index_needs_update = False # Index is valid
                            print(f"Loaded {len(all_pdf_paths)} paths from index.")
                        else:
                            print("Index file is empty. Re-indexing.")
                    else:
                        print(f"Index file folder ('{first_line}') does not match target folder ('{pdf_source_folder}'). Re-indexing.")
            except Exception as e:
                print(f"Error reading index file '{index_filename}': {e}. Re-indexing.")
                all_pdf_paths = [] # Force re-indexing on error

        # If index needs update (doesn't exist, wrong folder, empty, error)
        if index_needs_update:
            print(f"Indexing PDF files in '{pdf_source_folder}' (this may take a moment)...")
            # Use the function to list PDFs directly in the folder
            all_pdf_paths = list(tqdm(list_pdfs_in_folder(pdf_source_folder), desc="Indexing PDF files"))

            if all_pdf_paths: # Only write index if PDFs were found
                try:
                    with open(index_filename, 'w', encoding='utf-8') as f:
                        f.write(pdf_source_folder + '\n') # Write folder path as first line
                        for path in all_pdf_paths:
                            f.write(path + '\n') # Write each path on a new line
                    print(f"Index file '{index_filename}' created/updated successfully with {len(all_pdf_paths)} paths.")
                except Exception as e:
                    print(f"Error: Could not write index file '{index_filename}': {e}")
            else:
                 print(f"Indexing found no PDF files in the specified folder: {pdf_source_folder}. Exiting.")
                 return # Exit if no PDFs found during indexing
    # --- End of PDF Source Logic ---


    # --- Setup Scan Parameters ---
    # Ensure at least one scan action is requested if *not* using custom index implicitly
    # If custom index is used, we assume they want to scan all files in it unless --scan is also given
    if not args.use_custom_index and not args.scan_all and not args.scan:
         print("Note: No specific filter (--scan) provided. Analyzing all PDFs found in the folder (--scan-all assumed).")
         args.scan_all = True # Assume scanning all if no filter is given and not using custom index

    filter_keyword = args.scan if args.scan else None
    output_filename = args.output

    # Ensure all search terms are lowercase for consistent matching
    search_terms = [term.lower() for term in SEARCH_TERMS]

    # Double-check if we have paths before proceeding
    if not all_pdf_paths:
        print("No PDF file paths available to process. Exiting.")
        return
    print(f"Proceeding with analysis on {len(all_pdf_paths)} PDF files from {pdf_source_description}.\n")

    # --- Perform Analysis ---
    files_dict, counts, total_unique_count = find_and_process_pdfs(
        all_pdf_paths,
        search_terms,
        filter_keyword
    )

    # --- Report Generation ---
    report_lines = ["--- Search Results (Sentence-Level Analysis) ---"]
    # Add source description to the report
    report_lines.append(f"\nSource: {pdf_source_description}")
    report_lines.append(f"\n{'='*55}")
    if filter_keyword:
        report_lines.append(f"## Results for reports filtered by: '{filter_keyword}'")
    else:
        report_lines.append("## Results for all scanned reports")
    report_lines.append(f"{'='*55}")
    report_lines.append("### Individual Term Counts:")

    for term, count in sorted(counts.items()):
        report_lines.append(f"  - {term:<25}: {count} reports")

    report_lines.append(f"\n### Total Unique Reports in this Category: {total_unique_count}")
    report_lines.append("--- File List ---")

    for term in sorted(search_terms):
        files = sorted(list(files_dict.get(term, set())))
        if files:
            report_lines.append(f"\n#### Files containing '{term}':")
            for file_path in files:
                report_lines.append(f"{file_path}") # Use the actual path from the list/index

    report_lines.append("\n--- End of Report ---")

    # --- Save Report ---
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        print(f"\nAnalysis complete. Report successfully saved to: {os.path.abspath(output_filename)}")
    except Exception as e:
        print(f"\nError: Could not write report to file '{output_filename}'. {e}")

# Standard Python entry point check
if __name__ == "__main__":
    main()

"""
```

**Key Changes Summary:**

1.  **New Argument:** Added `--use-custom-index FILEPATH` to the argument parser.
2.  **Conditional Logic in `main()`:**
    * Checks if `args.use_custom_index` was provided.
    * **If Yes:**
        * Sets the source description for the report.
        * Checks if the custom index file exists. Exits with an error if not.
        * Reads all lines (PDF paths) from the custom index file into `all_pdf_paths`.
        * Sets `pdf_source_folder` and `index_filename` to `None` as they are not used for indexing in this mode.
        * **Skips the entire block that checks/creates/updates the managed index file.**
    * **If No:** The script proceeds with the previous logic, using `--folder` and `-i`/`--index` to manage the index file based on the folder content.
3.  **Error Handling:** Added `sys.exit(1)` if the custom index file isn't found or can't be read.
4.  **Reporting:** Updated the report header slightly to indicate whether a folder or a custom index was used as the source.
5.  **Filtering with Custom Index:** The `--scan KEYWORD` filtering logic now also works correctly when `--use-custom-index` is used, filtering the list *provided by* the custom index. Added checks for file existence within the filtering loop, as custom index paths might be invalid.

Now you can run the script like this to use a pre-existing list of files:

```bash
python selective_search_single_folder.py --use-custom-index "C:\Path\To\Your\filtered_pdf_list.txt" --scan-all
```

Or combine it with keyword filtering:

```bash
python selective_search_single_folder.py --use-custom-index "C:\Path\To\Your\filtered_pdf_list.txt" --scan "abdomen"

"""