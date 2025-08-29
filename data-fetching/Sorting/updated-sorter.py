import os
import shutil
import re
import logging
from datetime import datetime
from tqdm import tqdm
import pdfplumber

# --- CONFIGURATION ---
LOG_FILE = 'categorizer_optimized.log'
SKIPPED_REPORTS_FILE = 'skipped_reports_after_retry.txt'
REPROCESSED_SKIPPED_FILE = 'skipped_reports_final_retry.txt'

# Keywords that are body parts or scan types.
BODY_PART_KEYWORDS = [
    'KUB', 'MRI', 'XRAY', 'BRAIN', 'THORAX', 'HRCT', 'NCCT', 
    'PNS', 'CHEST', 'ABDOMEN', 'NECK', 'HEAD', 'SPINE', 'CECT'
]

# --- SCRIPT ---
def print_banner():
    """Prints a welcome banner to the console."""
    banner = r"""
    ############################################################
    #                                                          #
    #    S M A R T   R E P O R T   C A T E G O R I Z E R         #
    #            (Version 9.0 - Optimized)                     #
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
    Scans the destination directory once and creates an index (dictionary)
    mapping patient names to a list of their folder paths. This is a huge
    performance optimization.
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

def extract_info_from_filename(filename):
    """
    More robustly extracts patient's name and body part from a filename.
    """
    clean_filename = re.sub(r'\s*\(\d+\)', '', os.path.splitext(filename)[0]).strip()
    clean_filename = re.sub(r'\s+\d{1,2}\s*[mf]\s*', ' ', clean_filename, flags=re.IGNORECASE)
    
    for keyword in BODY_PART_KEYWORDS + ['CT']:
        clean_filename = re.sub(f'({keyword})', r' \1', clean_filename, flags=re.IGNORECASE)

    filename_upper = clean_filename.upper()
    
    name = None
    body_part = None
    description = ""

    split_regex = r'\s+(CECT|CT)\s+'
    match = re.search(split_regex, filename_upper)
    
    if match:
        split_point = match.start()
        name = clean_filename[:split_point].strip()
        description = clean_filename[split_point:].upper()
    else:
        split_point = -1
        for keyword in BODY_PART_KEYWORDS:
            position = filename_upper.find(f' {keyword}')
            if position != -1:
                if split_point == -1 or position < split_point:
                    split_point = position
        
        if split_point != -1:
            name = clean_filename[:split_point].strip()
            description = clean_filename[split_point:].upper()
        else:
            name = clean_filename

    if description:
        for keyword in BODY_PART_KEYWORDS:
            if keyword in description:
                body_part = keyword
                break

    if name:
        name = re.sub(r'^[^a-zA-Z]+', '', name)
        name = re.sub(r'[\s-]+$', '', name).lower().replace('cect', '').strip()
        name = re.sub(r'^(mrs|mr|ms)\s*\.?\s*', '', name, flags=re.IGNORECASE).strip()

        if name.upper() in BODY_PART_KEYWORDS or not name:
            logging.warning(f"Name parsing resulted in an invalid name for: {filename}")
            return None, None
        logging.info(f"Extracted name: '{name}', Body Part: '{body_part}' from '{filename}'.")
        return name, body_part
    else:
        logging.warning(f"Could not extract a valid name from filename: {filename}")
        return None, None

def extract_age_from_pdf(pdf_path):
    """Opens a PDF and searches for the patient's age."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages: return None
            first_page_text = pdf.pages[0].extract_text()
            if not first_page_text: return None
            
            match = re.search(r'(\d{1,3})\s*Y(RS|EARS|R)?', first_page_text, re.IGNORECASE)
            
            if match:
                age = match.group(1)
                logging.info(f"Extracted age '{age}' from '{pdf_path}'.")
                return age
            else:
                return None
    except Exception as e:
        logging.error(f"Failed to read PDF file '{pdf_path}'. Error: {e}")
        return None

def find_patient_folder(patient_name, body_part, source_pdf_path, folder_index):
    """Finds the patient folder using the pre-built index for speed."""
    
    search_names = [patient_name]
    if patient_name.lower().startswith('baby '):
        search_names.append(patient_name.lower().replace('baby ', '').strip())
    
    potential_matches = []
    for s_name in search_names:
        # The key for the index is space-separated, not a set of words
        s_name_key = " ".join(s_name.lower().split())
        if s_name_key in folder_index:
            potential_matches.extend(folder_index[s_name_key])
    
    potential_matches = list(set(potential_matches))

    if not potential_matches:
        return None, f"No folder found for patient '{patient_name}'"
        
    if len(potential_matches) == 1:
        return potential_matches[0], 'Success'

    logging.info(f"Found {len(potential_matches)} name matches for '{patient_name}'. Resolving with age...")
    age = extract_age_from_pdf(source_pdf_path)
    if not age:
        return None, f"Ambiguous name match for '{patient_name}' and could not get age from PDF"
    
    age_pattern = re.compile(f"_{age}Y", re.IGNORECASE)
    age_matches = [path for path in potential_matches if age_pattern.search(os.path.basename(path))]
    
    if len(age_matches) >= 1:
        logging.info(f"Found {len(age_matches)} name+age match(es). Selecting the first one.")
        return age_matches[0], 'Success'
    else:
         return None, f"Found name matches for '{patient_name}', but none with age '{age}'"

def get_skipped_files_list():
    """Reads the specified skipped reports file to get a list of files to reprocess."""
    if not os.path.exists(SKIPPED_REPORTS_FILE):
        return None
    
    skipped_files = []
    try:
        with open(SKIPPED_REPORTS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('- '):
                    filename = line[2:].strip()
                    skipped_files.append(filename)
        logging.info(f"Found {len(skipped_files)} files in '{SKIPPED_REPORTS_FILE}' to re-process.")
        return skipped_files
    except Exception as e:
        logging.error(f"Could not read {SKIPPED_REPORTS_FILE}. Error: {e}")
        return None

def process_files(source_dir, destination_dir, folder_index):
    """Processes PDF files, using the pre-built index."""
    
    pdf_files_to_process = get_skipped_files_list()
    if pdf_files_to_process is None:
        print(f"\n[INFO] '{SKIPPED_REPORTS_FILE}' not found. Processing all PDF files in source directory.")
        pdf_files_to_process = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
    else:
        print(f"\n[INFO] Found '{SKIPPED_REPORTS_FILE}'. Attempting to re-process {len(pdf_files_to_process)} failed files.")

    if not pdf_files_to_process:
        logging.info("No PDF files to process.")
        return [], 0
    
    skipped_files = []
    moved_count = 0
    progress_bar = tqdm(pdf_files_to_process, desc="Categorizing Reports", unit="file", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
    
    for filename in progress_bar:
        progress_bar.set_postfix_str(f"Processing: {filename[:30]}...")
        source_path = os.path.join(source_dir, filename)

        if not os.path.exists(source_path):
            skipped_files.append(('File Not Found in Source', filename))
            continue
        
        patient_name, body_part = extract_info_from_filename(filename)
        if not patient_name:
            skipped_files.append(('Name Parsing Failed', filename))
            continue
            
        matched_folder_path, reason = find_patient_folder(patient_name, body_part, source_path, folder_index)
        
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
        with open(REPROCESSED_SKIPPED_FILE, 'w') as f:
            f.write(f"--- Skipped Reports Log (After Retry) ---\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            
            for reason, files in sorted(grouped_skipped.items()):
                f.write(f"Reason: {reason} ({len(files)} files)\n")
                f.write("-" * 50 + "\n")
                for filename in sorted(files):
                    f.write(f"- {filename}\n")
                f.write("\n")

        logging.info(f"New skipped reports log created: {REPROCESSED_SKIPPED_FILE}")
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
        
    # --- OPTIMIZATION: Index folders once at the start ---
    folder_index = index_patient_folders(destination_dir)
    
    skipped_reports, moved_count = process_files(source_dir, destination_dir, folder_index)
    
    print(f"\n--- Processing Summary ---")
    print(f"Successfully moved: {moved_count} files.")
    print(f"Skipped: {len(skipped_reports)} files.")

    if skipped_reports:
        write_skipped_files_report(skipped_reports)
        print(f"A new list of remaining skipped files has been saved to '{REPROCESSED_SKIPPED_FILE}'")
    
    print(f"Check '{LOG_FILE}' for a detailed processing log.")
    logging.info("Processing complete.")

if __name__ == "__main__":
    main()
