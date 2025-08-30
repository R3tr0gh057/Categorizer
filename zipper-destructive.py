import os
import shutil
import logging
from tqdm import tqdm
import time

# --- CONFIGURATION ---
# IMPORTANT: Set this to the path of the folder you want to process.
BASE_FOLDER = r"" 
# Keywords to look for in folder names (case-insensitive).
KEYWORDS = ["chest", "head", "brain", "thorax"]
# File to keep track of completed folders. This allows the script to be resumed.
STATE_FILE = "processed_folders.log"
# File for detailed logging.
LOG_FILE = "processing_activity.log"

def setup_logging():
    """Configures logging to file and console."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler() # To also print to the console
        ]
    )

def load_processed_folders(state_file_path):
    """Loads the set of already processed folders from the state file."""
    if not os.path.exists(state_file_path):
        return set()
    with open(state_file_path, 'r') as f:
        # Using a set for fast lookups (O(1) average time complexity)
        processed = set(line.strip() for line in f)
        logging.info(f"Loaded {len(processed)} previously processed folders from state file.")
        return processed

def mark_folder_as_processed(folder_name, state_file_path):
    """Appends a folder name to the state file to mark it as complete."""
    with open(state_file_path, 'a') as f:
        f.write(f"{folder_name}\n")

def find_folders_to_process(base_dir, keywords, already_processed):
    """Scans the base directory and creates a list of folders to be zipped."""
    target_folders = []
    logging.info(f"Scanning '{base_dir}' for target folders...")
    
    # Use os.scandir() for better performance than os.listdir()
    for entry in os.scandir(base_dir):
        # 1. Check if it's a directory
        if not entry.is_dir():
            continue

        # 2. Check if it's already been processed
        if entry.name in already_processed:
            continue

        # 3. Check if its name contains any of the keywords
        if not any(keyword in entry.name.lower() for keyword in keywords):
            continue

        # 4. Check if it contains at least one PDF file
        try:
            if any(file.name.lower().endswith('.pdf') for file in os.scandir(entry.path)):
                target_folders.append(entry.path)
            else:
                logging.warning(f"Skipping '{entry.name}': Matches keywords but contains no PDF files.")
        except OSError as e:
            logging.error(f"Could not scan contents of '{entry.path}': {e}")

    return target_folders

def main():
    """Main function to execute the folder processing workflow."""
    setup_logging()
    logging.info("--- Starting Folder Processing Script ---")

    if not os.path.isdir(BASE_FOLDER):
        logging.error(f"Error: The specified BASE_FOLDER does not exist: '{BASE_FOLDER}'")
        return

    # Create full paths for state and log files to avoid clutter in other directories
    state_file_path = os.path.join(BASE_FOLDER, STATE_FILE)
    
    processed_folders_set = load_processed_folders(state_file_path)
    
    folders_to_zip = find_folders_to_process(BASE_FOLDER, KEYWORDS, processed_folders_set)

    if not folders_to_zip:
        logging.info("No new folders to process. All tasks are complete. Exiting.")
        return

    logging.info(f"Found {len(folders_to_zip)} new folders to process.")
    
    # Wrap the list with tqdm for a progress bar
    for folder_path in tqdm(folders_to_zip, desc="Zipping Folders", unit="folder"):
        folder_name = os.path.basename(folder_path)
        zip_name = os.path.join(BASE_FOLDER, folder_name)

        try:
            logging.info(f"Processing '{folder_name}'...")
            
            # Step 1: Create the zip archive
            shutil.make_archive(zip_name, 'zip', folder_path)
            logging.info(f"Successfully created archive: '{zip_name}.zip'")
            
            # --- DESTRUCTIVE FUNCTION REMOVED ---
            # The original folder is no longer deleted. The script now only
            # creates a zip archive and leaves the source folder intact.
            
            # Step 2: Mark as processed *after* the zip is created successfully
            mark_folder_as_processed(folder_name, state_file_path)
            
        except Exception as e:
            logging.error(f"!!! FAILED to process '{folder_name}': {e}")
            logging.error("This folder will be re-attempted on the next run.")
            # Add a small delay to prevent rapid-fire errors if there's a persistent issue
            time.sleep(1)

    logging.info("--- Script finished successfully ---")

if __name__ == "__main__":
    main()