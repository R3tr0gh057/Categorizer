import os
import shutil
import logging
import functools
import concurrent.futures

from tqdm import tqdm

LOG_FILE = 'zipper.log'

def print_banner():
    banner = r"""Z I P P E R 
    """
    print(banner)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
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

def get_paths_from_user():
    print("Please enter the required paths.")
    base_dir = input("Enter the BASE directory containing month folders: ").strip()
    zipped_dir = input("Enter the directory where zipped patient folders should be stored: ").strip()
    print(f"[INFO] Base directory: {base_dir}")
    print(f"[INFO] Zipped directory: {zipped_dir}")
    return base_dir, zipped_dir

# --- MODIFIED FUNCTION ---
def zip_and_move_folder(folder_path_to_zip, zipped_dir):
    """
    Worker function to process a single folder. Now includes detailed print statements.
    """
    base_name = os.path.basename(folder_path_to_zip.rstrip(os.sep))
    print(f"[INFO] Processing: {base_name}...", flush=True)

    # Check for .pdf files in the folder
    has_pdf = any(f.lower().endswith('.pdf') for f in os.listdir(folder_path_to_zip))
    if not has_pdf:
        with open('folders-without-report.txt', 'a', encoding='utf-8') as f:
            f.write(folder_path_to_zip + '\n')
        logging.warning(f"No PDF found in '{folder_path_to_zip}'. Skipping.")
        print(f"[WARNING] No PDF in '{base_name}', skipping.", flush=True)
        return

    try:
        zip_output_path = os.path.join(zipped_dir, base_name)
        os.makedirs(zipped_dir, exist_ok=True)
        
        # 1. Create the zip file
        archive_path = shutil.make_archive(zip_output_path, 'zip', root_dir=folder_path_to_zip)
        logging.info(f"Successfully zipped folder '{folder_path_to_zip}' to '{archive_path}'")
        
        # 2. Delete the original folder after successful zipping
        shutil.rmtree(folder_path_to_zip)
        logging.info(f"Successfully deleted original folder: '{folder_path_to_zip}'")
        
        print(f"[SUCCESS] Completed: {base_name}", flush=True)

    except Exception as e:
        logging.error(f"Error processing folder '{folder_path_to_zip}': {e}")
        print(f"[ERROR] Failed: {base_name}. Check log for details.", flush=True)

def process_folders(base_dir, zipped_dir):
    # This function's logic remains the same, only the tqdm description is updated.
    all_patient_folders = []
    if os.path.isdir(base_dir):
        month_folders = [os.path.join(base_dir, m) for m in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, m))]
        for month_folder in month_folders:
            for patient in os.listdir(month_folder):
                patient_path = os.path.join(month_folder, patient)
                if os.path.isdir(patient_path):
                    all_patient_folders.append(patient_path)

    if not all_patient_folders:
        logging.info("No patient folders found to zip in the source directory.")
        return

    completed_zips_basenames = set()
    if os.path.isdir(zipped_dir):
        for filename in os.listdir(zipped_dir):
            if filename.endswith('.zip'):
                base_name = os.path.splitext(filename)[0]
                completed_zips_basenames.add(base_name)

    folders_to_zip = []
    for folder_path in all_patient_folders:
        folder_basename = os.path.basename(folder_path)
        if folder_basename not in completed_zips_basenames:
            folders_to_zip.append(folder_path)

    total_count = len(all_patient_folders)
    completed_count = len(completed_zips_basenames)
    remaining_count = len(folders_to_zip)

    logging.info(f"Found {total_count} total patient folders.")
    print(f"INFO: Found {total_count} total patient folders.")
    if completed_count > 0:
        logging.info(f"Found {completed_count} already completed zips. Resuming.")
        print(f"INFO: Found {completed_count} already completed zips. Resuming.")

    if not folders_to_zip:
        logging.info("All folders have already been zipped. Nothing to do.")
        print("[SUCCESS] All folders have already been zipped. Nothing to do.")
        return

    logging.info(f"{remaining_count} folders remaining to be zipped.")
    print(f"INFO: {remaining_count} folders remaining to be zipped.")

    worker_func = functools.partial(zip_and_move_folder, zipped_dir=zipped_dir)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        list(tqdm(executor.map(worker_func, folders_to_zip), total=len(folders_to_zip), desc="Overall Progress"))

def main():
    print_banner()
    setup_logging()
    base_dir, zipped_dir = get_paths_from_user()
    process_folders(base_dir, zipped_dir)
    logging.info("Processing complete.")
    print("\n[SUCCESS] Processing complete. Check 'zipper.log' for details.")

if __name__ == "__main__":
    main()