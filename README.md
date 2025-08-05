# Categorizer

A Python automation toolkit for organizing and archiving PDF report files into patient folders, now split into two separate scripts for clarity and modularity.

## Features

- **Interactive Path Selection:** Both scripts prompt the user for the required directories.
- **Automatic File Parsing (sorter.py):** Extracts patient names and report dates from PDF filenames using a flexible pattern.
- **Date Range Matching (sorter.py):** Searches for the correct patient folder within a configurable date range to account for delays between scan and report dates.
- **Progress Bar:** Displays a progress bar for file processing using `tqdm`.
- **Logging & Status Messages:** Logs all actions and warnings to both the console and a log file (`categorizer.log`). All major actions also print a status message (success, warning, error, info) to the terminal for real-time feedback.
- **Automatic Zipping & Archiving (zipper.py):** Zips each patient folder and moves the resulting zip file to a user-specified directory. The original folder remains in place.

## Requirements

- Python 3.6+
- `tqdm` (for progress bar)

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Sorting/Categorizing Reports (sorter.py)

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

### 2. Zipping Patient Folders (zipper.py)

- **Prepare your folders:**
  - Ensure your patient folders are ready in a directory (e.g., the destination directory used above).

- **Run the zipper:**
  ```bash
  python zipper.py
  ```
  - Enter the path to the directory containing patient folders to zip.
  - Enter the path to the directory where zipped patient folders should be stored.

- **Result:**
  - Each patient folder will be zipped and the resulting zip file will be moved to the specified zipped directory. The original folders remain in place.
  - Review `categorizer.log` and the terminal output for a summary and any warnings or errors.

## Filename Format (sorter.py)

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
- **Log File:** All logs are written to `categorizer.log`.

## Troubleshooting

- Ensure the source, destination, and zipped directories exist and are accessible.
- The scripts will log warnings if they cannot parse a filename, find a matching folder, or zip a folder.
- If you do not see zipped folders in your specified directory, check for errors in the terminal or log file.

## License

See [LICENSE](LICENSE).
