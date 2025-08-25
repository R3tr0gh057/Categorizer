import os
import shutil
import configparser
import zipfile
from tqdm import tqdm

CONFIG_FILE = 'config.ini'

def load_config():
    """Loads directory paths from the config.ini file."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Error: Configuration file '{CONFIG_FILE}' not found.")
    config.read(CONFIG_FILE)
    try:
        files_dir = config['paths']['files_directory']
        zips_dir = config['paths']['zips_directory']
        return files_dir, zips_dir
    except KeyError:
        raise KeyError("Error: Make sure 'files_directory' and 'zips_directory' are set in config.ini")

def get_patient_folders(files_dir):
    """Walks the files directory to get a list of all patient folder paths."""
    patient_folders = []
    if not os.path.isdir(files_dir):
        print(f"Warning: Files directory not found at '{files_dir}'")
        return []
    
    # Go through each item in the files_dir (e.g., '20250101', '20250102')
    for date_folder in os.listdir(files_dir):
        date_folder_path = os.path.join(files_dir, date_folder)
        if os.path.isdir(date_folder_path):
            # Go through each item in the date_folder (e.g., 'BABLU_...', 'ASHA_YADAV_...')
            for patient_folder in os.listdir(date_folder_path):
                patient_folder_path = os.path.join(date_folder_path, patient_folder)
                if os.path.isdir(patient_folder_path):
                    patient_folders.append(patient_folder_path)
    return patient_folders

def get_zip_basenames(zips_dir):
    """Gets a set of filenames (without .zip) from the zips directory."""
    if not os.path.isdir(zips_dir):
        print(f"Warning: Zips directory not found at '{zips_dir}'")
        return set()
    
    return {os.path.splitext(f)[0] for f in os.listdir(zips_dir) if f.lower().endswith('.zip')}

def check_zip_content(zip_path, pdf_filename):
    """Safety Check: Verifies if the PDF exists inside the zip archive."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # zipfile stores paths with forward slashes, even on Windows
            pdf_in_zip = any(entry.endswith(pdf_filename) for entry in zf.namelist())
            return pdf_in_zip
    except (zipfile.BadZipFile, FileNotFoundError):
        return False

def main():
    """Main function to run the cleanup process."""
    print("--- Patient Folder Cleanup Script ---")

    try:
        files_dir, zips_dir = load_config()
        print(f"Files Directory: {files_dir}")
        print(f"Zips Directory:  {zips_dir}\n")
    except Exception as e:
        print(e)
        return

    all_patient_folders = get_patient_folders(files_dir)
    zipped_basenames = get_zip_basenames(zips_dir)

    folders_to_delete = []
    folders_not_zipped = []

    for folder_path in all_patient_folders:
        folder_basename = os.path.basename(folder_path)
        if folder_basename in zipped_basenames:
            folders_to_delete.append(folder_path)
        else:
            folders_not_zipped.append(folder_basename)

    # --- 1. Display folders that are NOT zipped ---
    print("-" * 40)
    if folders_not_zipped:
        print("The following patient folders are NOT zipped:")
        for folder_name in sorted(folders_not_zipped):
            print(f"  - {folder_name}")
    else:
        print("All patient folders appear to be zipped.")
    
    # --- 2. Ask user to verify deletion ---
    print("-" * 40)
    if not folders_to_delete:
        print("No folders to clean up. Exiting.")
        return

    print(f"🗑️ Found {len(folders_to_delete)} patient folders that are already zipped and can be deleted.")
    
    try:
        choice = input("Do you want to continue with deleting these folders? (yes/no): ").lower()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return
        
    if choice != 'yes':
        print("Operation cancelled. No files were deleted.")
        return

    # --- 3. Delete the folders with safety checks ---
    print("\nStarting deletion process with safety checks...")
    deleted_count = 0
    skipped_count = 0
    
    with tqdm(folders_to_delete, desc="Cleaning folders", unit="folder") as pbar:
        for folder_path in pbar:
            folder_basename = os.path.basename(folder_path)
            pbar.set_postfix_str(folder_basename)

            # Safety Check 1: Find a PDF in the source folder
            pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
            if not pdf_files:
                # print(f"  [SKIPPED] No PDF found in '{folder_basename}'.")
                skipped_count += 1
                continue
            
            pdf_filename = pdf_files[0]
            zip_path = os.path.join(zips_dir, folder_basename + '.zip')

            # Safety Check 2: Verify the PDF is inside the zip file
            if check_zip_content(zip_path, pdf_filename):
                try:
                    shutil.rmtree(folder_path)
                    deleted_count += 1
                except OSError as e:
                    print(f"\nError deleting folder {folder_path}: {e}")
                    skipped_count += 1
            else:
                # print(f"  [SKIPPED] PDF '{pdf_filename}' not found in the corresponding zip. Folder kept for safety.")
                skipped_count += 1
    
    print("\n--- Cleanup Complete ---")
    print(f"Successfully deleted: {deleted_count} folders.")
    print(f"Skipped for safety: {skipped_count} folders.")
    print("-" * 26)

if __name__ == "__main__":
    main()