import os
import pydicom
from collections import defaultdict
import re

# --- 1. SET THE FOLDER YOU WANT TO ANALYZE HERE ---
main_folder = r"C:\Users\dedse\Downloads\1.3.12.2.1107.5.1.7.137168.30000025081110302351200000019"

def find_body_part(dicom_dataset):
    """Attempts to find the body part from multiple common DICOM tags."""
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

# --- Main Analysis Logic ---
print(f"--- Starting Analysis in: {main_folder} ---\n")

# Data structures to hold unique values and their counts
unique_names = set()
unique_dates = set()
unique_body_parts = set()

name_counts = defaultdict(int)
date_counts = defaultdict(int)
body_part_counts = defaultdict(int)

files_scanned = 0
error_files = 0

for root, dirs, files in os.walk(main_folder):
    for filename in files:
        if not filename.lower().endswith('.dcm'):
            continue
        
        files_scanned += 1
        full_path = os.path.join(root, filename)
        
        try:
            ds = pydicom.dcmread(full_path, stop_before_pixels=True)

            # --- Extract all required data ---
            # For names, convert the special PersonName object to a string
            patient_name = str(ds.get('PatientName', 'Unknown_Name')).strip()
            study_date = ds.get('StudyDate', 'Unknown_Date').strip()
            body_part = find_body_part(ds)

            # Populate data structures
            unique_names.add(patient_name)
            unique_dates.add(study_date)
            unique_body_parts.add(body_part)
            
            name_counts[patient_name] += 1
            date_counts[study_date] += 1
            body_part_counts[body_part] += 1

        except Exception as e:
            error_files += 1
            print(f"Warning: Could not read {filename}. Reason: {e}")

# --- Final Reporting ---
print("\n--- ANALYSIS COMPLETE ---")

if files_scanned == 0:
    print("No DICOM (.dcm) files were found.")
else:
    # --- Individual Consistency Reports ---
    print(f"Total DICOM files scanned: {files_scanned-error_files} (readable)")

    # Name Report
    print("\n--- Patient Name Consistency ---")
    if len(unique_names) == 1:
        print(f"✅ Consistent Name: {list(unique_names)[0]}")
    else:
        print(f"⚠️ Inconsistent: Found {len(unique_names)} different names.")
        for name, count in name_counts.items():
            print(f"   - Name: '{name}' (found in {count} files)")

    # Date Report
    print("\n--- Study Date Consistency ---")
    if len(unique_dates) == 1:
        print(f"✅ Consistent Date: {list(unique_dates)[0]}")
    else:
        print(f"⚠️ Inconsistent: Found {len(unique_dates)} different dates.")
        for date, count in date_counts.items():
            print(f"   - Date: {date} (found in {count} files)")

    # Body Part Report
    print("\n--- Body Part Consistency ---")
    if len(unique_body_parts) == 1:
        print(f"✅ Consistent Body Part: {list(unique_body_parts)[0]}")
    else:
        print(f"⚠️ Inconsistent: Found {len(unique_body_parts)} different body parts.")
        for part, count in body_part_counts.items():
            print(f"   - Body Part: '{part}' (found in {count} files)")

    # --- Filename Feasibility Report ---
    print("\n" + "="*50)
    print("--- FILENAME FEASIBILITY REPORT ---")

    is_name_ok = len(unique_names) == 1 and "Unknown_Name" not in unique_names
    is_date_ok = len(unique_dates) == 1 and "Unknown_Date" not in unique_dates
    
    if is_name_ok and is_date_ok:
        # Get the consistent name and date
        the_name = list(unique_names)[0]
        the_date = list(unique_dates)[0]
        
        if len(unique_body_parts) == 1:
            the_body_part = list(unique_body_parts)[0]
            print("\n✅ Feasible: All components are consistent.")
            
        else:
            # Find the most common body part to use as a fallback
            most_common_part = max(body_part_counts, key=body_part_counts.get)
            the_body_part = most_common_part
            print(f"\n⚠️ Feasible: Name and Date are consistent. Using most common body part.")
            print(f"   (Most common body part is '{most_common_part}' with {body_part_counts[most_common_part]} files)")

        # Construct the proposed filename
        proposed_filename = (
            f"{clean_for_filename(the_name)}_"
            f"{the_date}_"
            f"CT_"
            f"{clean_for_filename(the_body_part)}"
        )
        print(f"\nProposed Filename Base: {proposed_filename}")

    else:
        print("\n❌ Not Feasible: A single filename cannot be constructed.")
        if not is_name_ok:
            print("   Reason: Patient Name is inconsistent or missing.")
        if not is_date_ok:
            print("   Reason: Study Date is inconsistent or missing.")
    print("="*50)