import os

def rename_all_zips_in_sequence():
    """
    Finds ALL zip files in a hardcoded directory, sorts them alphabetically,
    and renumbers them into the '###_DID.zip' format.
    """
    try:
        # --- PATH IS HARDCODED HERE ---
        folder_path = r"C:\Users\hp\Desktop\DID_Tool_Distribution\Lucknow"
        print(f"Targeting directory: {folder_path}\n")

        if not os.path.isdir(folder_path):
            print(f"❌ Error: The hardcoded path '{folder_path}' is not a valid directory.")
            return

        # 1. Find ALL files that end with .zip
        all_items = os.listdir(folder_path)
        zip_files = [f for f in all_items if f.lower().endswith('.zip')]

        if not zip_files:
            print("\nNo .zip files were found in this directory.")
            return

        # 2. Sort the files alphabetically
        zip_files.sort()
        print("Found files and sorted them alphabetically to determine renaming order.")

        start_number = 234
        end_number = 490

        # Check if the number of files matches the expected range
        if len(zip_files) != (end_number - start_number + 1):
            print(f"\n⚠️ Warning: Found {len(zip_files)} files, but the range {start_number}-{end_number} requires {end_number - start_number + 1} files.")
            print("The script will rename the files it found in sequence, but the final number might not be 490.")


        # 3. Generate the rename plan for user review
        rename_plan = []
        for i, old_filename in enumerate(zip_files):
            new_number = start_number + i
            new_filename = f"{new_number}_DID.zip"
            
            old_filepath = os.path.join(folder_path, old_filename)
            new_filepath = os.path.join(folder_path, new_filename)
            
            rename_plan.append((old_filename, new_filename, old_filepath, new_filepath))

        # 4. Show the preview and ask for confirmation
        print("\n--- RENAME PREVIEW ---")
        for old, new, _, _ in rename_plan:
            print(f"'{old}'  ->  '{new}'")
        print("------------------------")
        print(f"A total of {len(rename_plan)} files will be renamed.")
        
        confirm = input("Are you sure you want to proceed? (Type 'yes' to continue): ").lower()

        if confirm != 'yes':
            print("\nOperation cancelled by user. No files were changed.")
            return
            
        # 5. Execute the renaming process
        print("\nRenaming files...")
        renamed_count = 0
        # We rename in reverse to avoid conflicts where a new name might overwrite an existing old name
        for old_name, new_name, old_path, new_path in reversed(rename_plan):
            try:
                # To prevent errors (e.g., renaming A.zip to B.zip when B.zip already exists),
                # we first rename to a temporary name, then to the final name.
                temp_name = f"{new_name}.tmp"
                temp_path = os.path.join(folder_path, temp_name)
                
                os.rename(old_path, temp_path)
                os.rename(temp_path, new_path)
                
                renamed_count += 1
            except Exception as e:
                print(f"Could not rename '{old_name}'. Error: {e}")
        
        print(f"\n✅ Process complete. {renamed_count} files were successfully renamed.")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    rename_all_zips_in_sequence()