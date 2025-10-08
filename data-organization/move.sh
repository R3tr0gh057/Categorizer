#!/bin/bash

# The name of the folder where all files will be consolidated.
DEST_DIR="Images"

# --- Step 1: Create the destination directory ---
# The '-p' flag ensures that no error is thrown if the directory already exists.
mkdir -p "$DEST_DIR"
echo "Destination folder '$DEST_DIR' is ready."

# --- Step 2: Loop through all directories in the current location ---
# The '*/' pattern specifically selects only directories.
for SOURCE_DIR in */; do
    
    # Remove the trailing slash to get a clean directory name (e.g., "A/" becomes "A")
    DIR_NAME=${SOURCE_DIR%/}

    # --- Step 3: Skip the destination directory itself ---
    if [[ "$DIR_NAME" == "$DEST_DIR" ]]; then
        continue # Jumps to the next iteration of the loop
    fi

    echo -e "\nProcessing folder: '$DIR_NAME'..."

    # --- Step 4: Loop through each file within the source directory ---
    for FILE_PATH in "$SOURCE_DIR"*; do
    
        # Check if the item is a regular file before trying to copy it
        if [[ -f "$FILE_PATH" ]]; then
            # Extract just the filename from the path (e.g., "A/Z10.jpg" becomes "Z10.jpg")
            FILENAME=$(basename "$FILE_PATH")
            
            # --- Step 5: Create the new filename with the folder name as a prefix ---
            NEW_FILENAME="${DIR_NAME}${FILENAME}"
            
            # --- Step 6: Copy the file to the destination with its new name ---
            cp "$FILE_PATH" "${DEST_DIR}/${NEW_FILENAME}"
            echo "  ↳ Copied '$FILENAME' and renamed to '$NEW_FILENAME'"
        fi
    done
done

echo -e "\nAll files have been copied and renamed successfully!"