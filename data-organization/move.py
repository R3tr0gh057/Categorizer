import os
import shutil

def consolidate_files():
    """
    Copies files from multiple subfolders into a single 'Images' folder,
    prefixing each filename with its original parent folder's name.
    """
    # Define the destination folder name
    destination_folder_name = "Images"
    
    # Get the path of the current working directory where the script is located
    current_directory = os.getcwd()
    
    # Create the full path for the destination folder
    destination_path = os.path.join(current_directory, destination_folder_name)

    # --- Step 1: Ensure the destination folder exists ---
    if not os.path.exists(destination_path):
        os.makedirs(destination_path)
        print(f"Created destination folder: '{destination_folder_name}'")

    # --- Step 2: Loop through all items in the current directory ---
    for item_name in os.listdir(current_directory):
        item_path = os.path.join(current_directory, item_name)
        
        # --- Step 3: Check if the item is a directory and is NOT the destination folder ---
        if os.path.isdir(item_path) and item_name != destination_folder_name:
            source_folder_name = item_name
            print(f"\nProcessing folder: '{source_folder_name}'...")

            # --- Step 4: Loop through files inside the source folder ---
            for filename in os.listdir(item_path):
                source_file_path = os.path.join(item_path, filename)

                # Ensure we are only trying to copy files, not sub-directories
                if os.path.isfile(source_file_path):
                    
                    # --- Step 5: Create the new filename with the prefix ---
                    new_filename = source_folder_name + filename
                    
                    # Create the full path for the destination file
                    destination_file_path = os.path.join(destination_path, new_filename)
                    
                    # --- Step 6: Copy the file to the destination ---
                    shutil.copy2(source_file_path, destination_file_path)
                    print(f"  ↳ Copied '{filename}' and renamed to '{new_filename}'")

    print("\nAll files have been copied and renamed successfully!")

# Run the main function
if __name__ == "__main__":
    consolidate_files()