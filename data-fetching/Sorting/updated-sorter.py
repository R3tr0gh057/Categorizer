import os
import shutil
import re
import logging
from datetime import datetime
from tqdm import tqdm
import pdfplumber

# --- CONFIGURATION ---
LOG_FILE = 'categorizer_pdf_reader.log'
SKIPPED_REPORTS_FILE = 'skipped_reports_final.txt'

# --- SCRIPT ---
def print_banner():
    """Prints a welcome banner to the console."""
    banner = r"""
    ############################################################
    #                                                          #
    #    S M A R T   R E P O R T   C A T E G O R I Z E R         #
    #         (Version 10.2 - Robust PDF Reading)              #
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

def index_patient_folders(destination_dir):
    """
    Scans the destination directory once and creates an index mapping
    patient names to a list of their folder paths for performance.
    """
    print("\n[INFO] Indexing patient folders for faster matching... Please wait.")
    folder_index = {}
    for dir_name in tqdm(os.listdir(destination_dir), desc="Indexing Folders"):
        full_path = os.path.join(destination_dir, dir_name)
        if os.path.isdir(full_path):
            folder_parts = dir_name.split('_')
            name_parts = []
            for part in folder_parts:
                if re.match(r'^\d+Y', part, re.IGNORECASE):
                    break
                name_parts.append(part)
            
            folder_name_full = " ".join(name_parts).lower()
            
            if folder_name_full not in folder_index:
                folder_index[folder_name_full] = []
            folder_index[folder_name_full].append(full_path)
    print(f"[INFO] Indexing complete. Found {len(folder_index)} unique patient names.")
    return folder_index

def extract_info_from_pdf(pdf_path):
    """
    Extracts patient name, age, and body part directly from the PDF content.
    This is now the primary source of information.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                logging.warning(f"PDF has no pages: '{os.path.basename(pdf_path)}'")
                return None, None, None
            
            text = pdf.pages[0].extract_text()
            if not text:
                logging.warning(f"Could not extract text from: '{os.path.basename(pdf_path)}'")
                return None, None, None

            name, age, body_part = None, None, None

            # --- THE FIX IS HERE ---
            # This regex now correctly looks for the name between the 'NAME' and 'AGE' fields,
            # which is a more reliable pattern than looking for the 'DATE' field.
            name_match = re.search(r"PATIENT'S NAME\s*:\s*(.*?)\s*AGE\s*/\s*SEX", text, re.IGNORECASE | re.DOTALL)
            if name_match:
                name = name_match.group(1).strip()
                # Clean titles like MR., MRS., etc.
                name = re.sub(r'^(mrs|mr|ms|baby)\s*\.?\s*', '', name, flags=re.IGNORECASE).strip()

            # Extract Age (allows for spaces around the '/')
            age_match = re.search(r"AGE\s*/\s*SEX\s*:\s*(\d{1,3})\s*Y", text, re.IGNORECASE)
            if age_match:
                age = age_match.group(1).strip()

            # Extract Investigation (Body Part)
            investigation_match = re.search(r"INVESTIGATION\s*:\s*(.*)", text, re.IGNORECASE)
            if investigation_match:
                body_part_text = investigation_match.group(1).strip()
                # Extract the main keyword like BRAIN, KUB, etc.
                match = re.search(r'(BRAIN|KUB|THORAX|CHEST|ABDOMEN|NECK|HEAD|SPINE|PNS)', body_part_text, re.IGNORECASE)
                if match:
                    body_part = match.group(1)

            if name and age:
                 logging.info(f"PDF Read Success: Name='{name}', Age='{age}', Body Part='{body_part}' from '{os.path.basename(pdf_path)}'")
                 return name, age, body_part
            else:
                # Added more detailed logging to pinpoint the exact failure
                if not name:
                    logging.warning(f"Could not find Name in '{os.path.basename(pdf_path)}'")
                if not age:
                    logging.warning(f"Could not find Age in '{os.path.basename(pdf_path)}'")
                return None, None, None

    except Exception as e:
        logging.error(f"Failed to read PDF file '{os.path.basename(pdf_path)}'. Error: {e}")
        return None, None, None


def find_patient_folder(patient_name, age, body_part, folder_index):
    """Finds the patient folder using data extracted ONLY from the PDF."""
    
    search_name_key = " ".join(patient_name.lower().split())
    
    potential_matches = folder_index.get(search_name_key, [])

    if not potential_matches:
        return None, f"No folder found for patient '{patient_name}'"
        
    if len(potential_matches) == 1:
        return potential_matches[0], 'Success'

    # If multiple name matches, filter by age
    logging.info(f"Found {len(potential_matches)} name matches for '{patient_name}'. Verifying with age '{age}'...")
    
    age_pattern = re.compile(f"_{age}Y", re.IGNORECASE)
    age_matches = [path for path in potential_matches if age_pattern.search(os.path.basename(path))]
    
    if len(age_matches) >= 1:
        logging.info(f"Found {len(age_matches)} name+age match(es). Selecting the first one.")
        return age_matches[0], 'Success'
    else:
         return None, f"Found name matches for '{patient_name}', but none with age '{age}'"

def process_files(source_dir, destination_dir, folder_index):
    """Processes all PDF files in the source directory using PDF data."""
    
    pdf_files_to_process = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
    if not pdf_files_to_process:
        logging.info("No PDF files to process in source directory.")
        return [], 0
    
    skipped_files = []
    moved_count = 0
    progress_bar = tqdm(pdf_files_to_process, desc="Categorizing Reports", unit="file", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
    
    for filename in progress_bar:
        progress_bar.set_postfix_str(f"Processing: {filename[:30]}...")
        source_path = os.path.join(source_dir, filename)
        
        patient_name, age, body_part = extract_info_from_pdf(source_path)
        if not patient_name or not age:
            skipped_files.append(('PDF Read/Parse Failed', filename))
            continue
            
        matched_folder_path, reason = find_patient_folder(patient_name, age, body_part, folder_index)
        
        if not matched_folder_path:
            skipped_files.append((reason, filename))
            logging.warning(f"SKIPPED: {reason}. File: '{filename}'")
            continue
            
        if filename in os.listdir(matched_folder_path):
            reason = 'Target folder already contains this exact report'
            skipped_files.append((reason, filename))
            logging.warning(f"SKIPPED: Report '{filename}' already exists in target folder.")
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
    """Writes a formatted report of all remaining skipped files."""
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
            
            for reason, files in sorted(grouped_skipped.items()):
                f.write(f"Reason: {reason} ({len(files)} files)\n")
                f.write("-" * 50 + "\n")
                for filename in sorted(files):
                    f.write(f"- {filename}\n")
                f.write("\n")

        logging.info(f"New skipped reports log created: {SKIPPED_REPORTS_FILE}")
    except Exception as e:
        logging.error(f"Could not write new skipped reports file. Error: {e}")

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
        logging.error("Source or destination directory not found. Please check paths.")
        return
        
    folder_index = index_patient_folders(destination_dir)
    
    skipped_reports, moved_count = process_files(source_dir, destination_dir, folder_index)
    
    print(f"\n--- Processing Summary ---")
    print(f"Successfully moved: {moved_count} files.")
    print(f"Skipped: {len(skipped_reports)} files.")

    if skipped_reports:
        write_skipped_files_report(skipped_reports)
        print(f"A new list of remaining skipped files has been saved to '{SKIPPED_REPORTS_FILE}'")
    
    print(f"Check '{LOG_FILE}' for a detailed processing log.")
    logging.info("Processing complete.")

if __name__ == "__main__":
    main()
