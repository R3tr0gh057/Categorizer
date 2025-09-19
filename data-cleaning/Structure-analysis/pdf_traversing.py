import os
import fitz  # PyMuPDF
from tqdm import tqdm
import time

# --- CONFIGURATION ---
# IMPORTANT: Update these paths to your actual folder locations
REPORTS_FOLDER = r"C:\path\to\unmatched_reports"
MAIN_FOLDER = r"C:\path\to\matched_reports"

# The exact phrase to search for (case-sensitive)
SEARCH_PHRASE = "All on portal venous phase of CT abdomen, <3mm slice thickness"
OUTPUT_FILE = "output.txt"
# --- END CONFIGURATION ---

def find_all_pdfs_to_scan():
    """Gathers a list of all PDF file paths from both specified directories."""
    pdf_files = []
    
    # 1. Get PDFs from the flat REPORTS_FOLDER
    print(f"Finding PDFs in '{REPORTS_FOLDER}'...")
    if os.path.isdir(REPORTS_FOLDER):
        for filename in os.listdir(REPORTS_FOLDER):
            if filename.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(REPORTS_FOLDER, filename))
    else:
        print(f"Warning: Directory not found: {REPORTS_FOLDER}")

    # 2. Get PDFs from the subdirectories in MAIN_FOLDER
    print(f"Finding PDFs in subfolders of '{MAIN_FOLDER}'...")
    if os.path.isdir(MAIN_FOLDER):
        for dirpath, _, filenames in os.walk(MAIN_FOLDER):
            for filename in filenames:
                if filename.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(dirpath, filename))
    else:
         print(f"Warning: Directory not found: {MAIN_FOLDER}")
         
    return pdf_files

def search_phrase_in_pdf(pdf_path, phrase):
    """
    Searches for an exact phrase within a given PDF file.
    Returns True if the phrase is found, False otherwise.
    """
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text("text")
                if phrase in text:
                    return True
    except Exception as e:
        # Handles corrupted or unreadable PDFs gracefully
        print(f"\nCould not process file {os.path.basename(pdf_path)}: {e}")
        return False
    return False

def main():
    """Main function to run the PDF search and save the results."""
    print("--- PDF Search Script Initialized ---")
    start_time = time.time()
    
    # Step 1: Gather all potential PDF files
    all_pdfs = find_all_pdfs_to_scan()
    
    if not all_pdfs:
        print("\nNo PDF files found in the specified directories. Exiting.")
        return
        
    print(f"\nFound a total of {len(all_pdfs)} PDF(s) to scan.")
    
    # Step 2: Search each PDF and track progress
    print("Starting search...")
    matching_files = []
    
    # Using tqdm for a visual progress bar
    for pdf_path in tqdm(all_pdfs, desc="Scanning PDFs", unit="file"):
        if search_phrase_in_pdf(pdf_path, SEARCH_PHRASE):
            matching_files.append(pdf_path)
            
    # Step 3: Save the results to the output file
    print(f"\nSearch complete. Found {len(matching_files)} matching PDF(s).")
    
    try:
        with open(OUTPUT_FILE, 'w') as f:
            for path in matching_files:
                f.write(path + '\n')
        print(f"Results successfully saved to '{OUTPUT_FILE}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{OUTPUT_FILE}'. Reason: {e}")

    end_time = time.time()
    print(f"--- Script finished in {end_time - start_time:.2f} seconds ---")


if __name__ == "__main__":
    main()