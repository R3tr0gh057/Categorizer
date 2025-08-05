# Categorizer

A Python automation script for categorizing PDF report files into patient folders based on information extracted from the filenames and folder dates.

## Features

- **Interactive Path Selection:** Prompts the user to enter the source directory (where PDF reports are located) and the destination directory (where patient folders are stored).
- **Automatic File Parsing:** Extracts patient names and report dates from PDF filenames using a flexible pattern.
- **Date Range Matching:** Searches for the correct patient folder within a configurable date range to account for delays between scan and report dates.
- **Progress Bar:** Displays a progress bar for file processing using `tqdm`.
- **Logging & Status Messages:** Logs all actions and warnings to both the console and a log file (`categorizer.log`). All major actions also print a status message (success, warning, error, info) to the terminal for real-time feedback.
- **Automatic Zipping & Archiving:** After a report is copied into a patient's folder, that folder is zipped and the resulting zip file is moved to the `./lucknow` directory. The original patient folder is then deleted.

## Requirements

- Python 3.6+
- `tqdm` (for progress bar)

Install dependencies with:
```bash
pip install -r requirements.txt
```

## Usage

1. **Prepare your folders:**
   - Place all PDF reports in a source directory (e.g., `./REPORT`).
   - Ensure your destination directory contains subfolders named by date (e.g., `20240501`) and patient name.

2. **Run the script:**
   ```bash
   python categorizer.py
   ```

3. **Follow the prompts:**
   - Enter the path to your source directory (PDF reports).
   - Enter the path to your destination directory (patient folders).

4. **Check results:**
   - Processed files will be copied to the appropriate patient folder.
   - After each copy, the patient folder will be zipped and moved to the `./lucknow` directory, and the original folder will be deleted.
   - Review `categorizer.log` and the terminal output for a summary and any warnings or errors.

## Filename Format

The script expects PDF filenames in the format:
```
Report_of_<PATIENT_NAME>_<...>_<DAY>_<MONTH><YEAR>.pdf
```
Example:
```
Report_of_ANJU_NCCT HEAD_25_Jul25.pdf
```

## Configuration

- **Date Range:** The number of days to search back from the report date is set by `DATE_SEARCH_RANGE_DAYS` (default: 7 days).
- **Log File:** All logs are written to `categorizer.log`.
- **Zipped Directory:** The zipped patient folders are stored in the directory specified by `ZIPPED_DIR` (default: `./lucknow`).

## Troubleshooting

- Ensure the source and destination directories exist and are accessible.
- The script will log warnings if it cannot parse a filename or find a matching folder.
- If you do not see zipped folders in `./lucknow`, check for errors in the terminal or log file.

## License

See [LICENSE](LICENSE).
