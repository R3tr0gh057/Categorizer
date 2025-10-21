import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

try:
    import pdfplumber
    from tqdm import tqdm
except ImportError:
    print("Error: Required libraries not found.")
    print("Please install them using: pip install pdfplumber tqdm")
    sys.exit(1)

# --- Constants ---

# The keywords to search for. All must be present (case-insensitive).
REQUIRED_KEYWORDS: List[str] = ["PATIENT'S NAME", "REPORT", "INVESTIGATION"]

# The name of the output index file.
INDEX_FILE_NAME: str = "index.txt"

# --- Logging Setup ---

def setup_logging():
    """Configures the root logger for clean console output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)-8s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# --- Core Functions ---

def check_pdf_for_keywords(pdf_path: Path, keywords: List[str]) -> bool:
    """
    Reads a single PDF file and checks if all keywords are present.

    Args:
        pdf_path: The Path object of the PDF file to check.
        keywords: A list of keywords to search for.

    Returns:
        True if all keywords are found (case-insensitive), False otherwise.
    """
    try:
        full_text: str = ""
        with pdfplumber.open(pdf_path) as pdf:
            # Use tqdm for page-level progress (disabled in main loop)
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        if not full_text:
            logging.warning(f"Could not extract any text from {pdf_path.name}")
            return False

        # Perform a case-insensitive check
        full_text_lower = full_text.lower()
        keywords_lower = [k.lower() for k in keywords]

        if all(k in full_text_lower for k in keywords_lower):
            logging.info(f"Keywords FOUND in: {pdf_path.name}")
            return True
        else:
            return False

    except Exception as e:
        # Catch exceptions from corrupted, encrypted, or unreadable PDFs
        logging.error(f"Failed to process PDF {pdf_path.name}: {e}")
        return False

def find_and_index_pdfs(root_path: Path, keywords: List[str]) -> Tuple[List[Path], Dict[str, Any]]:
    """
    Traverses a directory, finds all PDFs, and checks them for keywords.

    Args:
        root_path: The root directory Path to start the scan from.
        keywords: The list of required keywords.

    Returns:
        A tuple containing:
        1. A list of Path objects for all matching PDFs.
        2. A dictionary of statistics.
    """
    stats = {
        "folders_traversed": 0,
        "files_scanned": 0,
        "pdfs_found_matching": 0,
        "total_pdfs_scanned": 0
    }
    relevant_pdfs: List[Path] = []
    
    logging.info(f"Starting scan in: {root_path}")
    logging.info("Step 1: Discovering all files and folders...")

    try:
        # Use rglob to recursively find all items
        all_paths = list(root_path.rglob('*'))
        
        all_files = [p for p in all_paths if p.is_file()]
        # Get unique parent directories
        all_folders = {p.parent for p in all_paths}
        
        stats["folders_traversed"] = len(all_folders)
        stats["files_scanned"] = len(all_files)
        
        pdf_files = [f for f in all_files if f.suffix.lower() == '.pdf']
        stats["total_pdfs_scanned"] = len(pdf_files)

        logging.info(f"Discovery complete. Found {stats['files_scanned']} files "
                     f"in {stats['folders_traversed']} folders.")
        
        if not pdf_files:
            logging.warning("No PDF files found in the specified directory.")
            return [], stats

        logging.info(f"Step 2: Analyzing {len(pdf_files)} PDF files for keywords...")
        
        # Process PDFs with a progress bar
        for pdf_path in tqdm(pdf_files, desc="Analyzing PDFs", unit="file", ncols=100):
            try:
                if check_pdf_for_keywords(pdf_path, keywords):
                    relevant_pdfs.append(pdf_path)
            except Exception as e:
                logging.error(f"Critical error checking {pdf_path.name}: {e}")

        stats["pdfs_found_matching"] = len(relevant_pdfs)
        return relevant_pdfs, stats

    except PermissionError as e:
        logging.error(f"Permission denied. Cannot scan directory: {e}")
        return [], stats
    except Exception as e:
        logging.error(f"An unexpected error occurred during traversal: {e}")
        return [], stats

def save_index_file(pdf_list: List[Path], output_file: str):
    """Saves the list of found PDF paths to a text file."""
    if not pdf_list:
        logging.info("No matching PDFs found. Index file will not be created.")
        return

    logging.info(f"Saving index of {len(pdf_list)} files to {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for pdf_path in pdf_list:
                # .resolve() gets the full, absolute path
                f.write(f"{pdf_path.resolve()}\n")
        logging.info(f"Successfully saved index to {output_file}")
    except IOError as e:
        logging.error(f"Could not write to index file {output_file}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving index: {e}")

def print_summary(stats: Dict[str, Any], duration: float):
    """Prints a final summary of the operation."""
    logging.info("--- Analysis Complete ---")
    print("\n" + "="*30)
    print("      ANALYSIS SUMMARY")
    print("="*30)
    print(f"  Folders Traversed:     {stats.get('folders_traversed', 0)}")
    print(f"  Total Files Scanned:   {stats.get('files_scanned', 0)}")
    print(f"  Total PDFs Analyzed:   {stats.get('total_pdfs_scanned', 0)}")
    print(f"  Matching PDFs Found:   {stats.get('pdfs_found_matching', 0)}")
    print(f"  Total Time Taken:      {duration:.2f} seconds")
    if stats.get('pdfs_found_matching', 0) > 0:
        print(f"\n  Index file saved to: {INDEX_FILE_NAME}")
    print("="*30 + "\n")

# --- Main Execution ---

def main():
    """Main function to run the script."""
    setup_logging()
    logging.info("--- Unstructured Analysis Script Initialized ---")
    
    print("\nWelcome to the Unstructured Analysis Script.")
    print("Please select a function to run:")
    print("-" * 30)
    print("  [1] Find & Index PDFs with Keywords")
    print("  [q] Quit")
    print("-" * 30)

    try:
        choice = input("Enter your choice: ").strip()

        if choice == '1':
            start_time = time.time()
            
            # 1. Get and validate path
            root_path_str = input("Enter the full path to the directory to scan: ").strip()
            if not root_path_str:
                logging.error("No path provided. Exiting.")
                sys.exit(1)
                
            root_path = Path(root_path_str)
            
            if not root_path.is_dir():
                logging.error(f"Error: Path '{root_path}' is not a valid directory or does not exist.")
                sys.exit(1)
            
            # 2. Run the analysis
            found_pdfs, stats = find_and_index_pdfs(root_path, REQUIRED_KEYWORDS)
            
            # 3. Save the results
            save_index_file(found_pdfs, INDEX_FILE_NAME)
            
            end_time = time.time()
            
            # 4. Print summary
            print_summary(stats, end_time - start_time)

        elif choice.lower() == 'q':
            logging.info("Exiting script. Goodbye!")
        
        else:
            logging.warning("Invalid choice. Please restart the script and select '1' or 'q'.")

    except KeyboardInterrupt:
        logging.warning("\nOperation cancelled by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"An unexpected fatal error occurred: {e}")
        sys.exit(1)

    logging.info("--- Script Finished ---")

if __name__ == "__main__":
    main()