# Categorizer

A Python automation toolkit for organizing and archiving PDF report files into patient folders, split into two scripts for clarity and modularity, plus a shell script for fast parallel zipping.

## Features

- **Interactive Path Selection:** All scripts prompt the user for the required directories.
- **Automatic File Parsing (sorter.py):** Extracts patient names and report dates from PDF filenames using a flexible pattern.
- **Advanced Sorting (updated-sorter.py):**
  - Extracts patient name, body part/scan type, and age (from PDF) for robust folder matching.
  - Multi-tiered matching: name → age → body part, to resolve ambiguities.
  - Moves (not copies) files to the matched folder, cleaning up the source directory.
  - Generates a detailed skipped reports log (`skipped_reports.txt`) with grouped reasons.
- **Date Range Matching (sorter.py):** Searches for the correct patient folder within a configurable date range to account for delays between scan and report dates.
- **Progress Bar:** Displays a progress bar for file processing using `tqdm` (Python scripts).
- **Logging & Status Messages:** Logs all actions and warnings to both a log file and the console. All major actions also print a status message (success, warning, error, info) to the terminal for real-time feedback.
- **Automatic Zipping & Archiving (zipper.py & shell/zipper.sh):**
  - Zips each patient folder (inside month folders) and moves the resulting zip file to a user-specified directory. The original folders remain in place.
  - **Checkpointing:** Skips patient folders that have already been zipped (if a .zip file with the same name exists in the destination).
  - **Parallel Zipping:** Uses all CPU cores to zip multiple folders at once for speed.

## Requirements

- Python 3.6+ (for Python scripts)
- `tqdm` (for progress bar in Python scripts)
- `pdfplumber` (for extracting age from PDF in updated-sorter.py)
- Bash, `zip`, and `xargs` (for shell/zipper.sh)

Install Python dependencies with:
```bash
pip install -r requirements.txt
```

## Configuration (config.ini)

Before running the scripts, create and edit a `config.ini` file in the project root with the following structure:

```
[SORTER]
source_dir = D:\Path\To\PDFs
destination_dir = D:\Path\To\PatientFolders

[ZIPPER]
base_dir = D:\Path\To\PatientFolders
zipped_dir = D:\Path\To\ZippedOutput
```

## Usage

### 1. Automated Workflow (`run_all.bat`)

- To run both the sorting and zipping steps in sequence, use the provided batch script:
  ```bat
  run_all.bat
  ```
- Ensure your `config.ini` is set up as described above.
- The script will run `sorter.py` and then `zipper.py` using the paths from `config.ini`.

### 2. Advanced Sorting/Categorizing Reports (`updated-sorter.py`)

- This script provides advanced matching using patient name, age (from PDF), and body part/scan type (from filename).
- **Interactive:** Prompts the user for the source and destination directories at runtime (does NOT use `config.ini`).
- **Moves** files to the matched folder (does not copy).
- **Generates** a detailed skipped reports log (`skipped_reports.txt`) with grouped reasons for each skipped file.
- Run with:
  ```bash
  python data-fetching/Sorting/updated-sorter.py
  ```
- At the end, check the terminal summary, `categorizer.log`, and `skipped_reports.txt` for details.

### 3. Sorting/Categorizing Reports (`sorter.py`)

- The script reads the source and destination directories from `config.ini` (see above).
- Run with:
  ```bash
  python fullauto/sorter.py
  ```
- No interactive input is required; all paths are taken from the config file.

### 4. Zipping Patient Folders (Python: `zipper.py`)

- The script reads the base and zipped directories from `config.ini` (see above).
- Run with:
  ```bash
  python fullauto/zipper.py
  ```
- No interactive input is required; all paths are taken from the config file.

### 5. Zipping Patient Folders (Shell: `shell/zipper.sh`)

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

## Filename Format (`sorter.py` and `updated-sorter.py`)

The sorter scripts expect PDF filenames to contain the patient name and (optionally) body part/scan type. Example:
```
ANJU NCCT HEAD 25_Jul25.pdf
RESHMA CT REPORT – THORAX (PLAIN AND CONTRAST).pdf
```

- `updated-sorter.py` will extract the name and body part/scan type from the filename, and age from the PDF content.

## Skipped Reports Log

- Both sorter scripts generate a log of skipped files, but `updated-sorter.py` creates a detailed, grouped report in `skipped_reports.txt`.
- Reasons include: ambiguous matches, missing folders, file already exists, parsing errors, etc.

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
