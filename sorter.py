import os
import shutil
import re
import logging
from datetime import datetime, timedelta
from tqdm import tqdm

# --- CONFIGURATION ---
# Set the number of days to search back and forward in time from the report's date.
DATE_SEARCH_RANGE_DAYS = 7
LOG_FILE = 'categorizer.log'
SKIPPED_REPORTS_FILE = 'skipped_reports.txt'

# --- SCRIPT ---
def print_banner():
    banner = r"""                                                         
                 C A T E G O R I Z E R                                                           
    """
    print(banner)
    print("[INFO] Banner displayed.")

def setup_logging():
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
    logging.info("Logging started.")
    print("[INFO] Logging started.")

def parse_filename(filename):
    pattern = re.compile(r'Report_of_(.+?)_.*?(\d{1,2})_([a-zA-Z]+)_(\d{2,4})\.pdf')
    match = pattern.match(filename)
    if not match:
        logging.warning(f"Filename did not match expected pattern: {filename}")
        print(f"[WARNING] Filename did not match expected pattern: {filename}")
        return None, None
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    try:
        name = match.group(1).strip().lower()
        day = int(match.group(2))
        month_str = match.group(3).lower()[:3]
        year_str = match.group(4)
        month = month_map.get(month_str)
        if not month:
            logging.warning(f"Unrecognized month '{month_str}' in file: {filename}")
            print(f"[WARNING] Unrecognized month '{month_str}' in file: {filename}")
            return None, None
        year = int(f"20{year_str}") if len(year_str) == 2 else int(year_str)
        report_date = datetime(year, month, day)
        logging.info(f"Parsed filename '{filename}' -> name: {name}, date: {report_date}")
        print(f"[SUCCESS] Parsed filename '{filename}' -> name: {name}, date: {report_date}")
        return name, report_date
    except (ValueError, IndexError) as e:
        logging.error(f"Could not parse date from filename '{filename}': {e}")
        print(f"[ERROR] Could not parse date from filename '{filename}': {e}")
        return None, None

def find_patient_folder(patient_name, report_date, destination_dir):
    # Split the name from the PDF into a set of individual words for matching.
    # e.g., "abbu hurera" -> {'abbu', 'hurera'}
    name_words = set(patient_name.split())

    for i in range(-DATE_SEARCH_RANGE_DAYS, DATE_SEARCH_RANGE_DAYS + 1):
        search_date = report_date + timedelta(days=i)
        date_folder_name = search_date.strftime('%Y%m%d')
        date_folder_path = os.path.join(destination_dir, date_folder_name)
        
        if os.path.exists(date_folder_path):
            for subfolder in os.listdir(date_folder_path):
                # Clean the folder name by removing numbers/symbols and split into words.
                # e.g., "ABBU HURERA_1.3.12..." -> {'abbu', 'hurera'}
                folder_text = re.sub(r'[^a-z\s]', '', subfolder.lower())
                folder_words = set(folder_text.split())

                # Check if all words from the PDF name exist in the folder name.
                if name_words.issubset(folder_words):
                    logging.info(f"Found match for '{patient_name}' in folder: {os.path.join(date_folder_path, subfolder)}")
                    print(f"[SUCCESS] Found match for '{patient_name}' in folder: {os.path.join(date_folder_path, subfolder)}")
                    return os.path.join(date_folder_path, subfolder)
                    
    logging.warning(f"No folder found for '{patient_name}' in the +/- {DATE_SEARCH_RANGE_DAYS} day search range.")
    print(f"[WARNING] No folder found for '{patient_name}' in the +/- {DATE_SEARCH_RANGE_DAYS} day search range.")
    return None

def get_paths_from_user():
    print("Please enter the required paths.")
    source_dir = input("Enter the SOURCE directory (where the PDF reports are located): ").strip()
    destination_dir = input("Enter the DESTINATION directory (where the patient folders are): ").strip()
    print(f"[INFO] Source directory: {source_dir}")
    print(f"[INFO] Destination directory: {destination_dir}")
    return source_dir, destination_dir

def process_files(source_dir, destination_dir):
    pdf_files = [f for f in os.listdir(source_dir) if f.lower().endswith('.pdf')]
    if not pdf_files:
        logging.info("No PDF files found in the source directory.")
        print("[INFO] No PDF files found in the source directory.")
        return []
    
    skipped_files = [] # Initialize list to track skipped files
    progress_bar = tqdm(pdf_files, desc="Categorizing Reports", unit="file")
    
    for filename in progress_bar:
        progress_bar.set_postfix_str(filename)
        patient_name, report_date = parse_filename(filename)
        
        if not patient_name or not report_date:
            logging.warning(f"Skipping file (could not parse): {filename}")
            print(f"[WARNING] Skipping file (could not parse): {filename}")
            skipped_files.append(('Parsing Failed', filename))
            continue
            
        matched_folder_path = find_patient_folder(patient_name, report_date, destination_dir)
        
        if not matched_folder_path:
            logging.warning(f"No matching folder found for '{patient_name}' within {DATE_SEARCH_RANGE_DAYS} days of {report_date.date()}. Skipping: {filename}")
            print(f"[WARNING] No matching folder found for '{patient_name}' within {DATE_SEARCH_RANGE_DAYS} days of {report_date.date()}. Skipping: {filename}")
            skipped_files.append((patient_name, filename))
            continue
            
        source_path = os.path.join(source_dir, filename)
        destination_path = os.path.join(matched_folder_path, filename)
        
        try:
            shutil.copy2(source_path, destination_path)
            logging.info(f"SUCCESS: Copied '{filename}' to '{destination_path}'")
            print(f"[SUCCESS] Copied '{filename}' to '{destination_path}'")
        except Exception as e:
            logging.error(f"FAILED to copy '{filename}'. Error: {e}")
            print(f"[ERROR] FAILED to copy '{filename}'. Error: {e}")
            
    return skipped_files

# --- NEW FUNCTION ---
def write_skipped_files_report(skipped_list):
    """Writes a formatted report of all skipped files to a text file."""
    if not skipped_list:
        logging.info("No files were skipped during the process.")
        return

    try:
        with open(SKIPPED_REPORTS_FILE, 'w') as f:
            f.write(f"--- Skipped Reports Log ---\n")
            f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*40 + "\n\n")
            
            parsing_failures = [item for item in skipped_list if item[0] == 'Parsing Failed']
            match_failures = [item for item in skipped_list if item[0] != 'Parsing Failed']

            if parsing_failures:
                f.write("Files That Failed to Parse (Incorrect Filename):\n")
                f.write("-" * 40 + "\n")
                for _, filename in parsing_failures:
                    f.write(f"- {filename}\n")
                f.write("\n")

            if match_failures:
                f.write("Files Where No Matching Folder Was Found:\n")
                f.write("-" * 40 + "\n")
                for name, filename in match_failures:
                    f.write(f"- Patient: {name.title():<25} | File: {filename}\n")

        logging.info(f"Skipped reports log created: {SKIPPED_REPORTS_FILE}")
        print(f"[INFO] A list of {len(skipped_list)} skipped files has been saved to '{SKIPPED_REPORTS_FILE}'")
    except Exception as e:
        logging.error(f"Could not write skipped reports file. Error: {e}")
        print(f"[ERROR] Could not write skipped reports file. Error: {e}")

def main():
    print_banner()
    setup_logging()
    source_dir, destination_dir = get_paths_from_user()
    
    if not os.path.isdir(source_dir):
        logging.error(f"Source directory not found: {source_dir}")
        print(f"[ERROR] Source directory not found: {source_dir}")
        return
        
    if not os.path.isdir(destination_dir):
        logging.error(f"Destination directory not found: {destination_dir}")
        print(f"[ERROR] Destination directory not found: {destination_dir}")
        return
        
    skipped_reports = process_files(source_dir, destination_dir)
    write_skipped_files_report(skipped_reports)
    
    logging.info("Processing complete.")
    print(f"[SUCCESS] Processing complete. Check '{LOG_FILE}' and '{SKIPPED_REPORTS_FILE}' for details.")

if __name__ == "__main__":
    main()