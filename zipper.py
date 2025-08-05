import os
import shutil
import logging

from tqdm import tqdm

LOG_FILE = 'zipper.log'

def print_banner():
    banner = r"""Z I P P E R 
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
        print(f"[SUCCESS] Zipped folder '{folder_path_to_zip}' to '{archive_path}'")
    except Exception as e:
        logging.error(f"Error zipping folder '{folder_path_to_zip}': {e}")
        print(f"[ERROR] Error zipping folder '{folder_path_to_zip}': {e}")

def process_folders(base_dir, zipped_dir):
    # Traverse all month folders in base_dir, then all patient folders inside each month folder
    month_folders = [os.path.join(base_dir, m) for m in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, m))]
    patient_folders = []
    for month_folder in month_folders:
        for patient in os.listdir(month_folder):
            patient_path = os.path.join(month_folder, patient)
            if os.path.isdir(patient_path):
                patient_folders.append(patient_path)
    if not patient_folders:
        logging.info("No patient folders found to zip.")
        print("[INFO] No patient folders found to zip.")
        return
    progress_bar = tqdm(patient_folders, desc="Zipping Patient Folders", unit="folder")
    for folder_path in progress_bar:
        progress_bar.set_postfix_str(os.path.basename(folder_path))
        zip_and_move_folder(folder_path, zipped_dir)

def main():
    print_banner()
    setup_logging()
    base_dir, zipped_dir = get_paths_from_user()
    if not os.path.isdir(base_dir):
        logging.error(f"Base directory not found: {base_dir}")
        print(f"[ERROR] Base directory not found: {base_dir}")
        return
    process_folders(base_dir, zipped_dir)
    logging.info("Processing complete.")
    print("[SUCCESS] Processing complete. Check 'zipper.log' for details.")

if __name__ == "__main__":
    main()