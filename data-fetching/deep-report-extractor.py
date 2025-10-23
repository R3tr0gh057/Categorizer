import os
import shutil
import time
from pathlib import Path

# --- Configuration ---
# Path to your index file containing a list of PDF paths, one per line.
# This assumes 'index.txt' is in the same folder as the script.
# You can change this to an absolute path if needed, e.g., Path(r"C:\MyData\index.txt")
INDEX_FILE = Path.cwd() / "index.txt" 
# --- End Configuration ---

def collect_and_zip_reports():
    """
    Reads a list of PDF paths from index.txt, copies them to a temporary
    directory, and zips them up.
    """
    
    # Get the directory where the script is running
    # This is where the temp folder and final zip will be created
    script_dir = Path.cwd()
    
    # 1. Define temporary folder and zip file names with a timestamp
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    temp_folder_name = f"temp_pdf_reports_{timestamp}"
    temp_folder_path = script_dir / temp_folder_name
    
    zip_file_name = f"all_reports_{timestamp}"
    # The full path to the zip file, but without the .zip extension
    # shutil.make_archive will add it automatically
    zip_base_path = script_dir / zip_file_name

    print(f"Script running in: {script_dir}")
    print(f"Using index file: {INDEX_FILE}")
    print(f"Temporary folder will be: {temp_folder_path}")
    print(f"Final ZIP file will be: {zip_base_path}.zip")

    # 2. Create the temporary folder
    try:
        temp_folder_path.mkdir(parents=True, exist_ok=True)
        print("\nStep 1: Created temporary folder.")
    except Exception as e:
        print(f"Error: Could not create temporary folder: {e}")
        return

    # 3. Collect all PDF file paths from the index file
    print("Step 2: Reading PDF paths from index file...")
    pdf_files_to_copy = []
    
    if not INDEX_FILE.exists():
        print(f"Error: Index file not found at {INDEX_FILE}")
        shutil.rmtree(temp_folder_path) # Clean up temp folder
        return

    missing_files = 0
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # Remove leading/trailing whitespace (like newlines)
            file_path_str = line.strip()
            
            if not file_path_str:
                continue # Skip empty lines

            pdf_path = Path(file_path_str)
            
            if pdf_path.exists() and pdf_path.is_file():
                pdf_files_to_copy.append(pdf_path)
            else:
                print(f"  - Warning: File not found or is not a file: {pdf_path}")
                missing_files += 1

    if missing_files > 0:
        print(f"  - Total files from index that are missing: {missing_files}")

    if not pdf_files_to_copy:
        print("\nNo valid PDF files found from the index. Cleaning up empty temp folder.")
        shutil.rmtree(temp_folder_path)
        print("Done.")
        return

    print(f"\nTotal PDF files to copy: {len(pdf_files_to_copy)}")

    # 4. Copy files to the temporary folder, handling name collisions
    print("Step 3: Copying files to temporary folder...")
    copied_count = 0
    failed_count = 0

    for pdf_path in pdf_files_to_copy:
        try:
            dest_path = temp_folder_path / pdf_path.name
            
            # Handle filename collisions (e.g., two "report.pdf" files)
            counter = 1
            while dest_path.exists():
                # Create a new name, e.g., "report (1).pdf"
                new_name = f"{pdf_path.stem} ({counter}){pdf_path.suffix}"
                dest_path = temp_folder_path / new_name
                counter += 1
                
            shutil.copy2(pdf_path, dest_path)
            copied_count += 1

            if copied_count % 100 == 0:
                print(f"  ... copied {copied_count} files ...")

        except Exception as e:
            print(f"  - Failed to copy {pdf_path}: {e}")
            failed_count += 1

    print(f"\nCopy complete. Successfully copied: {copied_count}, Failed: {failed_count}")

    if copied_count == 0:
        print("No files were successfully copied. Aborting zip process.")
        shutil.rmtree(temp_folder_path)
        print("Cleaned up temp folder.")
        return

    # 5. Create the ZIP file
    print("Step 4: Creating ZIP file...")
    try:
        archive_path = shutil.make_archive(
            base_name=zip_base_path,  # The path/name of the archive, minus extension
            format='zip',             # The archive format
            root_dir=temp_folder_path # The directory to zip
        )
        print(f"Successfully created ZIP file: {archive_path}")
    
    except Exception as e:
        print(f"Error: Could not create ZIP file: {e}")
        # Cleanup is skipped if zipping fails
        print(f"IMPORTANT: Temporary folder {temp_folder_path} was NOT deleted due to zip failure.")
        print("Please inspect the folder and zip manually if needed.")

    else:
        # 6. Clean up (remove) the temporary folder
        # This 'else' block only runs if the 'try' block above succeeded
        print("Step 5: Cleaning up temporary folder...")
        try:
            shutil.rmtree(temp_folder_path)
            print("Cleanup successful.")
        except Exception as e:
            print(f"Error: Could not remove temporary folder: {temp_folder_path}")
            print("Please remove it manually.")

    print("\n--- All tasks complete. ---")

if __name__ == "__main__":
    # This block ensures the function only runs when the script is executed directly
    collect_and_zip_reports()


