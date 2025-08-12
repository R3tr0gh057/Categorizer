import os
import pydicom
import re
from collections import defaultdict

# --- 1. SET THE BASE FOLDER CONTAINING ALL PATIENT FOLDERS ---
# This is the top-level directory where your patient folders are located.
base_folder = r"E:\InnoWave_Data\filestore"

def find_body_part(dicom_dataset):
    """
    Attempts to find the body part from multiple common DICOM tags,
    checking in order of preference.
    """
    tags_to_check = ['BodyPartExamined', 'StudyDescription', 'SeriesDescription']
    for tag in tags_to_check:
        value = dicom_dataset.get(tag, '').strip()
        if value:
            return value
    return "Unknown"

def clean_for_filename(text_to_clean):
    """A helper function to remove characters that are invalid in filenames."""
    text_to_clean = str(text_to_clean).replace('^', '_').replace(' ', '_')
    return re.sub(r'[^a-zA-Z0-9_-]', '', text_to_clean)

# --- MAIN SCRIPT LOGIC ---
print(f"--- Starting Folder Analysis and Renaming in: {base_folder} ---\n")

# Check if the base folder exists
if not os.path.isdir(base_folder):
    print(f"Error: The specified base folder does not exist: {base_folder}")
else:
    # Get the list of patient folders directly inside the base folder
    patient_folders = [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d))]

    if not patient_folders:
        print("No patient subfolders found to analyze.")
    else:
        renamed_count = 0
        for folder_name in patient_folders:
            folder_path = os.path.join(base_folder, folder_name)
            print(f"--- Analyzing Folder: {folder_name} ---")

            # Data structures for analysis
            unique_names = set()
            unique_dates = set()
            unique_body_parts = set()
            name_counts = defaultdict(int)
            date_counts = defaultdict(int)
            body_part_counts = defaultdict(int)
            files_scanned = 0
            
            # Scan all DICOM files within this folder
            for root, _, files in os.walk(folder_path):
                for filename in files:
                    if filename.lower().endswith('.dcm'):
                        files_scanned += 1
                        try:
                            ds = pydicom.dcmread(os.path.join(root, filename), stop_before_pixels=True)
                            
                            patient_name = str(ds.get('PatientName', 'Unknown_Name')).strip()
                            study_date = ds.get('StudyDate', 'Unknown_Date').strip()
                            body_part = find_body_part(ds)

                            unique_names.add(patient_name)
                            unique_dates.add(study_date)
                            unique_body_parts.add(body_part)
                            
                            name_counts[patient_name] += 1
                            date_counts[study_date] += 1
                            body_part_counts[body_part] += 1
                        except Exception:
                            # Ignore files that can't be read for this analysis
                            continue
            
            if files_scanned == 0:
                print("  -> No DICOM files found. Skipping.\n")
                continue

            # --- Feasibility Check ---
            is_name_ok = len(unique_names) == 1 and "Unknown_Name" not in unique_names
            is_date_ok = len(unique_dates) == 1 and "Unknown_Date" not in unique_dates

            if is_name_ok and is_date_ok:
                the_name = list(unique_names)[0]
                the_date = list(unique_dates)[0]
                
                if len(unique_body_parts) == 1:
                    the_body_part = list(unique_body_parts)[0]
                    print("  -> Analysis: Name, Date, and Body Part are consistent.")
                else:
                    # If body part is inconsistent, use the most common one
                    most_common_part = max(body_part_counts, key=body_part_counts.get)
                    the_body_part = most_common_part
                    print(f"  -> Analysis: Name and Date are consistent. Using most common body part: '{most_common_part}'")

                # Construct the new folder name
                new_folder_name_base = (
                    f"{clean_for_filename(the_name)}_"
                    f"{the_date}_"
                    f"CT_"
                    f"{clean_for_filename(the_body_part)}"
                )
                
                new_folder_name = f"{new_folder_name_base}_{folder_name}"
                
                original_path = os.path.join(base_folder, folder_name)
                new_path = os.path.join(base_folder, new_folder_name)

                # Rename the folder
                try:
                    os.rename(original_path, new_path)
                    print(f"  ✅ RENAMED to: {new_folder_name}\n")
                    renamed_count += 1
                except Exception as e:
                    print(f"  ❌ ERROR: Could not rename folder. Reason: {e}\n")

            else:
                print("  -> Analysis: Could not rename folder due to inconsistent data.")
                if not is_name_ok:
                    print("     - Reason: Patient Name is inconsistent or missing across files.")
                if not is_date_ok:
                    print("     - Reason: Study Date is inconsistent or missing across files.")
                print("") # Newline for spacing

        print(f"--- SCRIPT COMPLETE ---")
        print(f"Total folders renamed: {renamed_count}")