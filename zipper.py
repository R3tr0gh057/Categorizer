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

def zip_and_move_folder(folder_path_to_zip, zipped_dir):
    try:
        base_name = os.path.basename(folder_path_to_zip.rstrip(os.sep))
        zip_output_path = os.path.join(zipped_dir, base_name)
        os.makedirs(zipped_dir, exist_ok=True)
        archive_path = shutil.make_archive(zip_output_path, 'zip', root_dir=folder_path_to_zip)
        logging.info(f"Successfully zipped folder '{folder_path_to_zip}' to '{archive_path}'")
    except Exception as e:
        logging.error(f"Error zipping folder '{folder_path_to_zip}': {e}")

# --- MODIFIED process_folders FUNCTION WITH CHECKPOINTING ---
def process_folders(base_dir, zipped_dir):
    # 1. Get a complete list of all source folders that should be processed.
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
        print("[INFO] No patient folders found to zip in the source directory.")
        return

    # --- CHECKPOINT LOGIC START ---

    # 2. Get a set of base names of already completed .zip files for fast lookup.
    completed_zips_basenames = set()
    if os.path.isdir(zipped_dir):
        for filename in os.listdir(zipped_dir):
            if filename.endswith('.zip'):
                # Get the filename without the .zip extension
                base_name = os.path.splitext(filename)[0]
                completed_zips_basenames.add(base_name)

    # 3. Determine the list of folders that still need to be zipped.
    folders_to_zip = []
    for folder_path in all_patient_folders:
        folder_basename = os.path.basename(folder_path)
        if folder_basename not in completed_zips_basenames:
            folders_to_zip.append(folder_path)

    # 4. Report the status to the user.
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

    # --- CHECKPOINT LOGIC END ---

    # Create a partial function to pass the fixed 'zipped_dir' argument to the worker.
    worker_func = functools.partial(zip_and_move_folder, zipped_dir=zipped_dir)

    # Use ProcessPoolExecutor to run the zipping tasks in parallel on the REMAINING folders.
    with concurrent.futures.ProcessPoolExecutor() as executor:
        list(tqdm(executor.map(worker_func, folders_to_zip), total=len(folders_to_zip), desc="Zipping Remaining Folders"))


def main():
    print_banner()
    setup_logging()
    base_dir, zipped_dir = get_paths_from_user()
    process_folders(base_dir, zipped_dir)
    logging.info("Processing complete.")
    print("\n[SUCCESS] Processing complete. Check 'zipper.log' for details.")


if __name__ == "__main__":
    main()