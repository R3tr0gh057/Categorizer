# Lestest sorting algorith 27-08-2025 18:22

import os
import shutil
import re
import logging
from datetime import datetime
from tqdm import tqdm
import pdfplumber

# --- CONFIGURATION ---
LOG_FILE = 'categorizer.log'
SKIPPED_REPORTS_FILE = 'skipped_reports.txt'

# Expanded list of keywords that are body parts or scan types.
# The script will extract the first one it finds from the filename.
BODY_PART_KEYWORDS = [
    'BRAIN', 'THORAX', 'KUB', 'HRCT', 'NCCT', 'PNS', 'CHEST', 
    'ABDOMEN', 'NECK', 'HEAD', 'SPINE'
]

# --- SCRIPT ---
def print_banner():
    """Prints a welcome banner to the console."""
    banner = r"""
    ############################################################
    #                                                          #
    #          S M A R T   R E P O R T   C A T E G O R I Z E R   #
    #            (Version 5.0 - Body Part Check)               #
    #                                                          #
    ############################################################
    """
    print(banner)

def setup_logging():
    """Configures logging to both a file and the console."""
    if logging.getLogger().hasHandlers():
        logging.getLogger().handlers.clear()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=LOG_FILE,
        filemode='w'
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)
    logging.info("Logging started. Console and file logs are active.")

def extract_info_from_filename(filename):
    """
    Extracts patient's name and the body part/scan type from a filename.
    """
    clean_filename = re.sub(r'\s*\(\d+\)', '', os.path.splitext(filename)[0])
    filename_upper = clean_filename.upper()
    
    split_point = -1
    body_part = None

    # Find the earliest position of any keyword
    for keyword in BODY_PART_KEYWORDS:
        # Search for the keyword with spaces/dashes around it to be more specific
        position = filename_upper.find(f' {keyword}')
        if position != -1:
            if split_point == -1 or position < split_point:
                split_point = position
                body_part = keyword

    if split_point != -1:
        name = clean_filename[:split_point].strip()
    else:
        # If no keyword found, assume the whole thing is the name
        name = clean_filename.strip()

    if name:
        name = re.sub(r'[\s-]+$', '', name).lower()
        logging.info(f"Extracted name: '{name}', Body Part: '{body_part}' from '{filename}'.")
        return name, body_part
    else:
        logging.warning(f"Could not extract a valid name from filename: {filename}")
        return None, None

def extract_age_from_pdf(pdf_path):
    """Opens a PDF and searches for the patient's age (e.g., '28 YRS')."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                logging.warning(f"PDF file has no pages: '{pdf_path}'.")
                return None
            first_page_text = pdf.pages[0].extract_text()
            if not first_page_text:
                logging.warning(f"Could not extract text from '{pdf_path}'.")
                return None
            
            match = re.search(r'(\d{1,3})\s*Y(RS|EARS|R)?', first_page_text, re.IGNORECASE)
            
            if match:
                age = match.group(1)
                logging.info(f"Extracted age '{age}' from '{pdf_path}'.")
                return age
            else:
                logging.warning(f"Could not find an age pattern in '{pdf_path}'.")
                return None
    except Exception as e:
        if "No pages found" in str(e):
             logging.warning(f"Could not read dummy/empty PDF: '{pdf_path}'. Cannot extract age.")
        else:
            logging.error(f"Failed to read PDF file '{pdf_path}'. Error: {e}")
        return None

def find_patient_folder(patient_name, body_part, source_pdf_path, destination_dir):
    """Finds the patient folder using name, age, and body part to resolve ambiguities."""
    name_from_report = set(patient_name.lower().split())
    potential_matches = []

    for dir_name in os.listdir(destination_dir):
        full_path = os.path.join(destination_dir, dir_name)
        if os.path.isdir(full_path):
            folder_parts = dir_name.split('_')
            name_parts = []
            for part in folder_parts:
                if re.match(r'^\d+Y', part):
                    break
                name_parts.append(part)
            
            folder_name_full = " ".join(name_parts)
            folder_words = set(folder_name_full.lower().split())
            
            if name_from_report.issubset(folder_words):
                potential_matches.append(full_path)
    
    if not potential_matches:
        return None, f"No folder found for patient '{patient_name}'"
        
    if len(potential_matches) == 1:
        return potential_matches[0], 'Success'

    # --- Tier 2: Filter by Age ---
    logging.info(f"Found {len(potential_matches)} name matches for '{patient_name}'. Resolving with age...")
    age = extract_age_from_pdf(source_pdf_path)
    if not age:
        return None, f"Ambiguous name match for '{patient_name}' and could not get age from PDF"
    
    age_matches = [path for path in potential_matches if f"_{age}Y" in os.path.basename(path)]
    
    if len(age_matches) == 0:
         return None, f"Found name matches for '{patient_name}', but none with age '{age}'"
    if len(age_matches) == 1:
        return age_matches[0], 'Success'

    # --- Tier 3: Filter by Body Part ---
    logging.info(f"Found {len(age_matches)} name+age matches for '{patient_name}'. Resolving with body part...")
    if not body_part:
        return None, f"Ambiguous name+age match for '{patient_name}' and no body part found in filename"

    final_matches = [path for path in age_matches if f"_{body_part.upper()}_" in os.path.basename(path).upper()]

    if len(final_matches) == 1:
        return final_matches[0], 'Success'
    else:
        return None, f"Could not resolve ambiguity for '{patient_name}'. Found {len(final_matches)} folders with age '{age}' and body part '{body_part}'"


def process_files(source_dir, destination_dir):
    """Processes each PDF file in the source directory."""
    pdf_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        logging.info("No PDF files found in the source directory.")
        return [], 0
    
    skipped_files = []
    moved_count = 0
    progress_bar = tqdm(pdf_files, desc="Categorizing Reports", unit="file", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
    
    for filename in progress_bar:
        progress_bar.set_postfix_str(f"Processing: {filename[:30]}...")
        source_path = os.path.join(source_dir, filename)
        
        patient_name, body_part = extract_info_from_filename(filename)
        if not patient_name:
            skipped_files.append(('Name Parsing Failed', filename))
            logging.warning(f"SKIPPED: Could not parse name from '{filename}'.")
            continue
            
        matched_folder_path, reason = find_patient_folder(patient_name, body_part, source_path, destination_dir)
        
        if not matched_folder_path:
            skipped_files.append((reason, filename))
            logging.warning(f"SKIPPED: {reason}. File: '{filename}'")
            continue
            
        # Check if a file with the exact same name already exists in the target folder.
        if filename in os.listdir(matched_folder_path):
            reason = 'Target folder already contains this exact report'
            skipped_files.append((reason, filename))
            logging.warning(f"SKIPPED: The report '{filename}' already exists in '{os.path.basename(matched_folder_path)}'.")
            continue

        destination_path = os.path.join(matched_folder_path, filename)
        
        try:
            shutil.move(source_path, destination_path)
            logging.info(f"SUCCESS: Moved '{filename}' to '{os.path.basename(matched_folder_path)}'")
            moved_count += 1
        except Exception as e:
            reason = f'File Move Error: {e}'
            skipped_files.append((reason, filename))
            logging.error(f"FAILED to move '{filename}'. Error: {e}")
            
    return skipped_files, moved_count

def write_skipped_files_report(skipped_list):
    """Writes a formatted report of all skipped files."""
    if not skipped_list:
        return

    grouped_skipped = {}
    for reason, filename in skipped_list:
        if reason not in grouped_skipped:
            grouped_skipped[reason] = []
        grouped_skipped[reason].append(filename)

    try:
        with open(SKIPPED_REPORTS_FILE, 'w') as f:
            f.write(f"--- Skipped Reports Log ---\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            
            for reason, files in grouped_skipped.items():
                f.write(f"Reason: {reason} ({len(files)} files)\n")
                f.write("-" * 50 + "\n")
                for filename in files:
                    f.write(f"- {filename}\n")
                f.write("\n")

        logging.info(f"Skipped reports log created: {SKIPPED_REPORTS_FILE}")
    except Exception as e:
        logging.error(f"Could not write skipped reports file. Error: {e}")

def get_paths_from_user():
    """Gets source and destination paths from the user."""
    source_dir = input("Enter the SOURCE directory (with PDF reports): ").strip()
    destination_dir = input("Enter the DESTINATION directory (with patient folders): ").strip()
    return source_dir, destination_dir

def main():
    """Main function to run the script."""
    print_banner()
    setup_logging()
    
    source_dir, destination_dir = get_paths_from_user()
    if not os.path.isdir(source_dir) or not os.path.isdir(destination_dir):
        logging.error("Source or destination directory not found. Please check the paths and try again.")
        return
        
    skipped_reports, moved_count = process_files(source_dir, destination_dir)
    
    print(f"\n--- Processing Summary ---")
    print(f"Successfully processed: {moved_count} files.")
    print(f"Skipped: {len(skipped_reports)} files.")

    if skipped_reports:
        write_skipped_files_report(skipped_reports)
        print(f"Check '{SKIPPED_REPORTS_FILE}' for a list of skipped files and reasons.")
    
    print(f"Check '{LOG_FILE}' for a detailed processing log.")
    logging.info("Processing complete.")

if __name__ == "__main__":
    main()
