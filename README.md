# Categorizer

A Python automation toolkit for organizing and archiving PDF report files into patient folders, split into two scripts for clarity and modularity, plus a shell script for fast parallel zipping.

## Features

- **Interactive Path Selection:** All scripts prompt the user for the required directories.
- **Automatic File Parsing (sorter.py):** Extracts patient names and report dates from PDF filenames using a flexible pattern.
- **Date Range Matching (sorter.py):** Searches for the correct patient folder within a configurable date range to account for delays between scan and report dates.
- **Progress Bar:** Displays a progress bar for file processing using `tqdm` (Python scripts).
- **Logging & Status Messages:** Logs all actions and warnings to both the console and a log file (`categorizer.log` for sorting, `zipper.log` for zipping). All major actions also print a status message (success, warning, error, info) to the terminal for real-time feedback.
- **Automatic Zipping & Archiving (zipper.py & shell/zipper.sh):**
  - Zips each patient folder (inside month folders) and moves the resulting zip file to a user-specified directory. The original folders remain in place.
  - **Checkpointing:** Skips patient folders that have already been zipped (if a .zip file with the same name exists in the destination).
  - **Parallel Zipping:** Uses all CPU cores to zip multiple folders at once for speed.

## Requirements

- Python 3.6+ (for Python scripts)
- `tqdm` (for progress bar in Python scripts)
- Bash, `zip`, and `xargs` (for shell/zipper.sh)

Install Python dependencies with:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Sorting/Categorizing Reports (`sorter.py`)

- **Prepare your folders:**
  - Place all PDF reports in a source directory (e.g., `./REPORT`).
  - Ensure your destination directory contains subfolders named by date (e.g., `20240501`) and patient name.

- **Run the sorter:**
  ```bash
  python sorter.py
  ```
  - Enter the path to your source directory (PDF reports).
  - Enter the path to your destination directory (patient folders).

- **Result:**
  - Processed files will be copied to the appropriate patient folder.
  - Review `categorizer.log` and the terminal output for a summary and any warnings or errors.

### 2. Zipping Patient Folders (Python: `zipper.py`)

- **Prepare your folders:**
  - Ensure your patient folders are organized inside month folders (e.g., `base_dir/202405/PatientA`, `base_dir/202405/PatientB`, etc.).

- **Run the zipper:**
  ```bash
  python zipper.py
  ```
  - Enter the path to the **base directory** containing month folders.
  - Enter the path to the directory where zipped patient folders should be stored.

- **Result:**
  - Each patient folder (inside each month folder) will be zipped and the resulting zip file will be moved to the specified zipped directory. The original folders remain in place.
  - Already-zipped folders are skipped automatically (checkpointing).
  - Zipping is performed in parallel for speed.
  - Review `zipper.log` and the terminal output for a summary and any warnings or errors.

### 3. Zipping Patient Folders (Shell: `shell/zipper.sh`)

- **Prepare your folders:**
  - Same structure as above: patient folders inside month folders.
  - Requires Bash, `zip`, and `xargs` (available on most Unix-like systems).

- **Run the shell zipper:**
  ```bash
  bash shell/zipper.sh
  ```
  - Enter the path to the **base directory** containing patient folders (should contain month folders).
  - Enter the path to the directory where zipped folders should be stored.

- **Result:**
  - All patient folders (inside all month folders) will be zipped in parallel (4 at a time by default) and saved to the destination directory.
  - Already-zipped folders are skipped (checkpointing).
  - The script prints progress and a final summary to the terminal.

## Folder Structure for Zipping

```
base_dir/
  202405/
    PatientA/
    PatientB/
  202406/
    PatientC/
    PatientD/
```
- Only the patient folders (e.g., `PatientA`, `PatientB`, etc.) will be zipped.

## Filename Format (`sorter.py`)

The sorter script expects PDF filenames in the format:
```
Report_of_<PATIENT_NAME>_<...>_<DAY>_<MONTH><YEAR>.pdf
```
Example:
```
Report_of_ANJU_NCCT HEAD_25_Jul25.pdf
```

## Configuration

- **Date Range (sorter.py):** The number of days to search back from the report date is set by `DATE_SEARCH_RANGE_DAYS` (default: 7 days).
- **Log Files:**
  - Sorting: `categorizer.log`
  - Zipping (Python): `zipper.log`

## Troubleshooting

- Ensure the source, destination, and zipped directories exist and are accessible.
- The scripts will log warnings if they cannot parse a filename, find a matching folder, or zip a folder.
- If you do not see zipped folders in your specified directory, check for errors in the terminal or log file.
- If you rerun zipper.py or shell/zipper.sh, they will skip folders that have already been zipped.

## License

See [LICENSE](LICENSE).
