import os
import pydicom
import re
from collections import defaultdict
from datetime import datetime

# --- 1. SET THE BASE FOLDER CONTAINING ALL PATIENT FOLDERS ---
# This is the top-level directory.
# Use a raw string (r"...") on Windows to handle backslashes correctly.
base_folder = r"E:\InnoWave_Data\filestore"

# --- 2. CONFIGURE LOG FILE ---
# A log file will be created in the same directory where the script is run.
log_filename = f"dicom_analysis_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"


def find_body_part(dicom_dataset):
    """
    Attempts to find the body part from multiple common DICOM tags,
    checking in order of preference.
    """
    # Order of preference for finding the body part
    tags_to_check = ['BodyPartExamined', 'StudyDescription', 'SeriesDescription']
    
    for tag in tags_to_check:
        value = dicom_dataset.get(tag, '').strip()
        if value:
            return value
            
    return "Unknown"


def analyze_patient_folder(folder_path):
    """
    Analyzes a single patient folder and returns a formatted string report.
    """
    report_lines = []
    report_lines.append(f"--- Analysis for Folder: {os.path.basename(folder_path)} ---")

    # Data structures for this specific folder's analysis
    unique_patients = set()
    unique_body_parts = set()
    unique_study_dates = set()  # ADDED: For tracking unique dates
    patient_counts = defaultdict(int)
    body_part_counts = defaultdict(int)
    study_date_counts = defaultdict(int) # ADDED: For counting date occurrences
    files_scanned = 0
    error_files = 0

    # Walk through the specific patient folder
    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            if not filename.lower().endswith('.dcm'):
                continue

            files_scanned += 1
            full_path = os.path.join(root, filename)
            
            try:
                # Use stop_before_pixels for speed, as we only need the header
                ds = pydicom.dcmread(full_path, stop_before_pixels=True)

                # Use PatientID as the primary identifier for consistency
                patient_id = ds.get('PatientID', 'Unknown_Patient_ID').strip()
                body_part = find_body_part(ds)
                study_date = ds.get('StudyDate', 'Unknown_Date').strip() # ADDED: Get Study Date

                unique_patients.add(patient_id)
                unique_body_parts.add(body_part)
                unique_study_dates.add(study_date) # ADDED: Add date to set
                patient_counts[patient_id] += 1
                body_part_counts[body_part] += 1
                study_date_counts[study_date] += 1 # ADDED: Increment date count

            except Exception as e:
                # Catch any error during DICOM reading and log it
                error_files += 1
                # This detailed error won't go to the log, but is useful for debugging
                # print(f"DEBUG: Error reading {full_path}. Reason: {e}")

    # --- Build the report string ---
    if files_scanned == 0:
        report_lines.append("No DICOM (.dcm) files were found in this folder.")
        return "\n".join(report_lines)

    report_lines.append(f"\nTotal DICOM files scanned: {files_scanned}")
    if error_files > 0:
        report_lines.append(f"Files that could not be read: {error_files}")

    # Patient Consistency Report
    report_lines.append("\n--- Patient Consistency Report ---")
    if len(unique_patients) == 1:
        report_lines.append(f"✅ Consistent: All {files_scanned - error_files} readable files belong to the same patient.")
        report_lines.append(f"   - Patient ID: {list(unique_patients)[0]}")
    else:
        report_lines.append(f"⚠️ Inconsistent: Found {len(unique_patients)} different patients.")
        for patient, count in patient_counts.items():
            report_lines.append(f"   - Patient ID: {patient} (found in {count} files)")

    # Study Date Consistency Report (NEW SECTION)
    report_lines.append("\n--- Study Date Consistency Report ---")
    if len(unique_study_dates) == 1:
        report_lines.append(f"✅ Consistent: All {files_scanned - error_files} readable files share the same study date.")
        report_lines.append(f"   - Study Date: {list(unique_study_dates)[0]}")
    else:
        report_lines.append(f"⚠️ Inconsistent: Found {len(unique_study_dates)} different study dates.")
        for date, count in study_date_counts.items():
            report_lines.append(f"   - Study Date: {date} (found in {count} files)")

    # Body Part Consistency Report
    report_lines.append("\n--- Body Part Consistency Report ---")
    if len(unique_body_parts) == 1:
        report_lines.append(f"✅ Consistent: All {files_scanned - error_files} readable files appear to be for the same body part.")
        report_lines.append(f"   - Body Part: {list(unique_body_parts)[0]}")
    else:
        report_lines.append(f"⚠️ Inconsistent: Found {len(unique_body_parts)} different body parts.")
        for part, count in body_part_counts.items():
            report_lines.append(f"   - Body Part: '{part}' (found in {count} files)")
    
    return "\n".join(report_lines)


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # Check if the base folder exists
    if not os.path.isdir(base_folder):
        print(f"Error: The specified base folder does not exist: {base_folder}")
    else:
        print(f"Starting analysis. Results will be saved to '{log_filename}'")
        
        # Open the log file to write the reports
        with open(log_filename, 'w') as log_file:
            log_file.write(f"DICOM Consistency Analysis Report\n")
            log_file.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"Base Folder Analyzed: {base_folder}\n")
            log_file.write("="*80 + "\n\n")

            # Get the list of patient folders directly inside the base folder
            try:
                patient_folders = [os.path.join(base_folder, d) for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))]
                
                if not patient_folders:
                    print("No patient subfolders found in the base folder.")
                    log_file.write("No patient subfolders found in the base folder.")
                else:
                    for folder_path in patient_folders:
                        print(f"Analyzing folder: {os.path.basename(folder_path)}...")
                        report = analyze_patient_folder(folder_path)
                        log_file.write(report + "\n\n" + "-"*80 + "\n\n")
                    
                    print(f"\nAnalysis complete. Log file '{log_filename}' has been created.")

            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                print(error_message)
                log_file.write(error_message)