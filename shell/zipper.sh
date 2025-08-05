#!/bin/bash

# A parallel, resumable script to zip subdirectories.

echo "Z I P P E R - Shell Script Version"
echo "------------------------------------"

# --- 1. Get User Input ---
read -p "Enter the BASE directory containing patient folders: " BASE_DIR
read -p "Enter the directory where zipped folders should be stored: " ZIPPED_DIR

# --- Validate Input ---
if [ ! -d "$BASE_DIR" ]; then
    echo "Error: Base directory '$BASE_DIR' not found."
    exit 1
fi

# Create the destination directory if it doesn't exist
mkdir -p "$ZIPPED_DIR"

# --- 2. Find All Source Folders ---
# -mindepth 2 assumes a structure like /Base/Month/Patient and skips the Month folders.
ALL_FOLDERS=($(find "$BASE_DIR" -mindepth 2 -type d))
TOTAL_COUNT=${#ALL_FOLDERS[@]}

echo "INFO: Found $TOTAL_COUNT total patient folders."

# --- 3. Checkpoint Logic: Determine what to zip ---
FOLDERS_TO_ZIP=()
COMPLETED_COUNT=0

for FOLDER_PATH in "${ALL_FOLDERS[@]}"; do
    BASENAME=$(basename "$FOLDER_PATH")
    
    # Check if a zip file with this name already exists in the destination
    if [ -f "$ZIPPED_DIR/$BASENAME.zip" ]; then
        ((COMPLETED_COUNT++))
    else
        FOLDERS_TO_ZIP+=("$FOLDER_PATH")
    fi
done

# --- 4. Report Status and Exit if Complete ---
REMAINING_COUNT=${#FOLDERS_TO_ZIP[@]}

if [ "$COMPLETED_COUNT" -gt 0 ]; then
    echo "INFO: Found $COMPLETED_COUNT already completed zips. Resuming."
fi

if [ "$REMAINING_COUNT" -eq 0 ]; then
    echo "SUCCESS: All folders have already been zipped."
    exit 0
fi

echo "INFO: $REMAINING_COUNT folders remaining to be zipped."

# --- 5. The Parallel Zipping Engine ---

printf "%s\n" "${FOLDERS_TO_ZIP[@]}" | xargs -P 4 -I {} bash -c '
    # Get the full path of the folder to be zipped from the input
    FOLDER_PATH="{}"
    
    # Get the destination directory from the parent script
    ZIPPED_DIR_ARG="'"$ZIPPED_DIR"'"

    # Extract the base name (e.g., "Patient_A")
    BASENAME=$(basename "$FOLDER_PATH")
    
    echo "Zipping: $BASENAME"
    
    # Zipping command.
    (
        cd "$(dirname "$FOLDER_PATH")" && \
        zip -r -q "$ZIPPED_DIR_ARG/$BASENAME.zip" "$BASENAME"
    )
'

echo "------------------------------------"
echo "SUCCESS: Processing complete."