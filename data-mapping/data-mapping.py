import pydicom
import pypdf
import re
import shutil
import os
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any

# --- 1. CONFIGURATION: UPDATE THESE PATHS ---

# Path to the root folder containing all patient DICOM folders
DICOM_ROOT_DIR = Path("/path/to/your/dicom_patient_folders")

# List of paths to folders containing the PDF reports
PDF_REPORT_DIRS = [
    Path("/path/to/your/pdf_reports_folder_1"),
    Path("/path/to/your/pdf_reports_folder_2"),
]

# Log file to record successes and failures
LOG_FILE = Path("./matching_log.txt")

# --- 2. REGEX: PDF DATA EXTRACTION ---
# These are built from your sample.
# They are the most fragile part and may need tuning if your PDF layouts vary.
# We compile them once for efficiency.

# Captures "PREET" from "MR. PREET"
NAME_REGEX = re.compile(
    r"PATIENT'S NAME\s*:\s*(?:MR\.|MS\.|MRS\.)?\s*([A-Z\s]+?)\n", re.IGNORECASE
)
# Captures "15" and "M" from "15 YRS/M"
AGE_SEX_REGEX = re.compile(r"AGE/SEX\s*:\s*(\d+)\s*YRS/([MF])", re.IGNORECASE)
# Captures "CT" and "ABDOMEN" from "CT ABDOMEN AND PELVIS"
INVEST_REGEX = re.compile(
    r"INVESTIGATION\s*:\s*(\w+)\s+(ABDOMEN|CHEST|HEAD|PELVIS|KUB)[\w\s]*", re.IGNORECASE
)


# --- 3. HELPER FUNCTIONS ---

def normalize_dicom_name(dicom_name: str) -> str:
    """Normalizes DICOM PatientName (e.g., 'LUCKY 8Y/M') to just 'LUCKY'."""
    # Split on space and take the first part
    return dicom_name.split()[0].upper()

def normalize_pdf_name(pdf_name: str) -> str:
    """Normalizes PDF name (e.g., ' PREET ') to 'PREET'."""
    return pdf_name.strip().upper()

def normalize_age(age_str: str) -> str:
    """Normalizes DICOM age (e.g., '008Y') or PDF age ('15') to just digits."""
    # Remove any non-numeric characters
    return re.sub(r'[^0-9]', '', age_str)


def extract_data_from_pdf(pdf_path: Path) -> Optional[Dict[str, str]]:
    """
    Extracts and normalizes required data from a single PDF's first page.
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            # Convert to UPPERCASE once to simplify all regex matching
            text = reader.pages[0].extract_text().upper()

        name_match = NAME_REGEX.search(text)
        age_sex_match = AGE_SEX_REGEX.search(text)
        invest_match = INVEST_REGEX.search(text)

        # If any piece of data is missing, we can't build a key
        if not (name_match and age_sex_match and invest_match):
            return None

        # Extract and normalize data
        return {
            "name": normalize_pdf_name(name_match.group(1)),
            "age": normalize_age(age_sex_match.group(1)),
            "sex": age_sex_match.group(2).upper(),
            "modality": invest_match.group(1).upper(),
            "body_part": invest_match.group(2).upper(),
        }
    except Exception as e:
        print(f"  [!] Error reading PDF {pdf_path.name}: {e}")
        return None


# --- 4. CORE LOGIC: PHASE 1 (INDEXING) ---

def index_dicom_folders(
    root_dir: Path
) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    """
    Walks the DICOM directory and builds an index (hash map).
    
    Key: (PatientName, PatientAge, PatientSex)
    Value: {path, modality, body_part}
    """
    print(f"Starting DICOM indexing in: {root_dir}\nThis may take a moment...")
    dicom_index = {}
    
    # Use os.walk, as it's efficient for finding the *first* file in a directory
    for root, dirs, files in os.walk(root_dir):
        dcm_file = None
        # Find the first .dcm file in the current folder
        for f in files:
            if f.lower().endswith('.dcm'):
                dcm_file = Path(root) / f
                break
        
        if dcm_file:
            try:
                # CRITICAL EFFICIENCY: stop_before_pixels=True
                # This reads *only* the header (tags), not the heavy image data.
                ds = pydicom.dcmread(dcm_file, stop_before_pixels=True)
                
                # Get tags safely
                name = getattr(ds, 'PatientName', None)
                age = getattr(ds, 'PatientAge', None)
                sex = getattr(ds, 'PatientSex', None)
                modality = getattr(ds, 'Modality', None)
                body_part = getattr(ds, 'BodyPartExamined', None)

                # If we have the core tags, create an index entry
                if all((name, age, sex, modality, body_part)):
                    # Normalize data to create a reliable key
                    norm_name = normalize_dicom_name(str(name))
                    norm_age = normalize_age(str(age))
                    norm_sex = str(sex).upper()
                    
                    # This is the unique key for the patient
                    key = (norm_name, norm_age, norm_sex)
                    
                    if key not in dicom_index:
                        # Store the data we need for matching
                        dicom_index[key] = {
                            "path": Path(root), # The folder to copy reports into
                            "modality": str(modality).upper(),
                            "body_part": str(body_part).upper(),
                            "source_file": dcm_file.name,
                        }
                
                # EFFICIENCY: We found a .dcm file and indexed this folder.
                # Tell os.walk not to go any deeper into its subfolders.
                dirs[:] = []
                
            except Exception as e:
                print(f"  [!] Skipping folder {root} (could not read DICOM): {e}")

    print(f"\n--- DICOM Indexing Complete. Found {len(dicom_index)} unique patients. ---")
    return dicom_index


# --- 5. CORE LOGIC: PHASE 2 & 3 (MATCH & COPY) ---

def process_pdf_reports(
    pdf_dirs: List[Path], dicom_index: Dict[Tuple[str, str, str], Dict[str, Any]]
):
    """
    Processes all PDFs, looks them up in the index, and copies on match.
    """
    print("Starting PDF matching process...")
    matched_count = 0
    unmatched_count = 0
    log_entries = []

    for pdf_dir in pdf_dirs:
        print(f"\nScanning PDF folder: {pdf_dir}")
        # Use rglob to find all .pdf files in this folder and all subfolders
        for pdf_path in pdf_dir.rglob('*.pdf'):
            # 1. Extract data from PDF
            pdf_data = extract_data_from_pdf(pdf_path)
            
            if not pdf_data:
                log_entries.append(f"[FAIL] {pdf_path.name}: Could not extract data (check PDF format/regex).")
                unmatched_count += 1
                continue

            # 2. Create the lookup key from PDF data
            pdf_key = (pdf_data["name"], pdf_data["age"], pdf_data["sex"])
            
            # 3. Perform the fast index lookup
            dicom_match = dicom_index.get(pdf_key)
            
            if dicom_match:
                # 4. PRIMARY MATCH FOUND. Perform secondary check.
                pdf_mod = pdf_data["modality"]
                pdf_body = pdf_data["body_part"]
                dicom_mod = dicom_match["modality"]
                dicom_body = dicom_match["body_part"]
                
                # Check that Modality matches AND PDF body part is in DICOM body part
                # (e.g., PDF "ABDOMEN" is in DICOM "ABDOMEN" or "ABDOMEN PELVIS")
                if pdf_mod == dicom_mod and pdf_body in dicom_body:
                    # 5. SUCCESS: Copy the file
                    try:
                        dest_folder = dicom_match["path"]
                        dest_file = dest_folder / pdf_path.name
                        
                        # Use copy2 to preserve file metadata (like creation time)
                        shutil.copy2(pdf_path, dest_file)
                        
                        log_entries.append(f"[SUCCESS] {pdf_path.name} -> {dest_file}")
                        matched_count += 1
                    except Exception as e:
                        log_entries.append(f"[FAIL] {pdf_path.name}: Matched but FAILED TO COPY. Error: {e}")
                        unmatched_count += 1
                else:
                    # Key matched, but secondary check failed
                    log_entries.append(f"[FAIL] {pdf_path.name}: Key match, but secondary check failed. PDF({pdf_mod}/{pdf_body}) vs DICOM({dicom_mod}/{dicom_body})")
                    unmatched_count += 1
            else:
                # 4. NO MATCH in index
                log_entries.append(f"[FAIL] {pdf_path.name}: No DICOM patient found for key: {pdf_key}")
                unmatched_count += 1
                
    # --- 6. REPORTING ---
    print("\n--- PDF Matching Complete ---")
    print(f"  Successfully Matched: {matched_count}")
    print(f"  Failed to Match:    {unmatched_count}")
    
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"--- Matching Log ---\n")
            f.write(f"Matched: {matched_count} | Unmatched: {unmatched_count}\n\n")
            f.write("\n".join(log_entries))
        print(f"\nDetailed log written to: {LOG_FILE}")
    except Exception as e:
        print(f"\n[!] Critical Error: Could not write log file! {e}")


# --- 7. SCRIPT EXECUTION ---

def main():
    # Check if paths are still placeholders
    if "/path/to/your" in str(DICOM_ROOT_DIR):
        print("="*60)
        print("ERROR: Please update the placeholder paths in the script.")
        print("Set 'DICOM_ROOT_DIR' and 'PDF_REPORT_DIRS' at the top.")
        print("="*60)
        return

    # Phase 1: Build the index
    try:
        dicom_index = index_dicom_folders(DICOM_ROOT_DIR)
        
        if not dicom_index:
            print("No DICOM files were found or indexed. Please check 'DICOM_ROOT_DIR'.")
            return
            
        # Phase 2 & 3: Process PDFs and copy files
        process_pdf_reports(PDF_REPORT_DIRS, dicom_index)
        
    except FileNotFoundError:
        print(f"Error: A specified path does not exist. Please check your configuration.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()