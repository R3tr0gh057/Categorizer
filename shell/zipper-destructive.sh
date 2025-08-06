#!/bin/bash

# A parallel, resumable script that zips subdirectories, skips those without reports,
# and deletes the original folder after successful zipping.

echo "Z I P P E R - Shell Script Version (Zips and Deletes)"
echo "------------------------------------------------------------------"
echo "🔥🔥🔥 WARNING: THIS SCRIPT WILL DELETE THE ORIGINAL FOLDERS 🔥🔥🔥"
echo "      AFTER THEY ARE SUCCESSFULLY ZIPPED. USE WITH CAUTION."
read -p "Press [Enter] to continue or Ctrl+C to abort."

# --- 1. Get User Input ---
read -p "Enter the BASE directory containing patient folders: " BASE_DIR
read -p "Enter the directory where zipped folders should be stored: " ZIPPED_DIR

# --- Validate Input ---
if [ ! -d "$BASE_DIR" ]; then
    echo "Error: Base directory '$BASE_DIR' not found."
    exit 1
fi

# Create the destination directory
mkdir -p "$ZIPPED_DIR"

# Define and initialize the log file for skipped folders
LOG_FILE="$ZIPPED_DIR/skipped_folders_log.log"
export LOG_FILE # Export for use in xargs sub-shell
# Clear any old log and add a header for the new run
echo "Log of folders skipped for missing a PDF report. Run started: $(date)" > "$LOG_FILE"
echo "-------------------------------------------------------------------" >> "$LOG_FILE"


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

echo "INFO: $REMAINING_COUNT folders remaining to be processed."

# --- 5. The Parallel Zipping Engine ---

printf "%s\n" "${FOLDERS_TO_ZIP[@]}" | xargs -P 4 -I {} bash -c '
    # Get the full path of the folder to be zipped from the input
    FOLDER_PATH="{}"
    
    # Get the destination directory from the parent script
    ZIPPED_DIR_ARG="'"$ZIPPED_DIR"'"

    # Extract the base name (e.g., "Patient_A")
    BASENAME=$(basename "$FOLDER_PATH")
    
    # Check for PDF and decide to ZIP or SKIP
    if [ -z "$(find "$FOLDER_PATH" -maxdepth 1 -type f -name "*.pdf" -print -quit)" ]; then
        # IF TRUE (no PDF found): Log the issue, display a warning, and SKIP.
        echo "$BASENAME" >> "$LOG_FILE"
        echo "WARNING: ''$BASENAME'' is missing a PDF report. SKIPPING this folder."
    else
        # IF FALSE (PDF was found): Proceed with zipping the folder.
        echo "Zipping: $BASENAME"

        # --- MODIFIED BEHAVIOR: ZIP AND THEN DELETE ---
        # The `&&` operator is a safety mechanism.
        # `rm -rf` will ONLY run if the `zip` command before it succeeds.
        (
            cd "$(dirname "$FOLDER_PATH")" && \
            zip -r -q "$ZIPPED_DIR_ARG/$BASENAME.zip" "$BASENAME" && \
            rm -rf "$BASENAME"
        ) && echo "DELETED: $BASENAME"
    fi
'

echo "------------------------------------------------------------------"
echo "SUCCESS: Processing complete."
echo "INFO: A log of folders that were skipped has been saved to: $LOG_FILE"