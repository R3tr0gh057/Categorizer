import os

# --- Configuration ---

# 1. The name of your big file
INPUT_FILENAME = "-data-for-analysis-lucknow.txt"  # <--- CHANGE THIS

# 2. How many reports to put in each smaller file
REPORTS_PER_FILE = 100

# 3. The prefix for the new files (e.g., "split_report_1.txt")
OUTPUT_PREFIX = "split_report"

# 4. The text that marks the beginning of a report (case-insensitive)
START_MARKER = "--- impression from:"

# --- End Configuration ---

all_reports = []
current_report_lines = []

try:
    print(f"Reading from '{INPUT_FILENAME}'...")
    with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
        for line in f:
            # Check if the line is the start of a new report
            if line.strip().lower().startswith(START_MARKER):
                # If we have a report being built, save it to the list
                if current_report_lines:
                    all_reports.append("".join(current_report_lines))
                # Start the new report
                current_report_lines = [line]
            else:
                # If it's not a new report, add the line to the current one
                if current_report_lines:  # Only add lines if we've found the first marker
                    current_report_lines.append(line)
    
    # Add the very last report in the file
    if current_report_lines:
        all_reports.append("".join(current_report_lines))

except FileNotFoundError:
    print(f"\n--- ERROR ---")
    print(f"The file '{INPUT_FILENAME}' was not found.")
    print("Please make sure the file is in the same directory as the script,")
    print("or change the INPUT_FILENAME variable to the full file path.")
    exit()
except Exception as e:
    print(f"An error occurred while reading the file: {e}")
    exit()

if not all_reports:
    print(f"No reports found in '{INPUT_FILENAME}'.")
    print(f"Check if the START_MARKER is correct. It's currently set to: '{START_MARKER}'")
    exit()

print(f"Successfully read {len(all_reports)} total reports.")
print(f"Splitting into new files with {REPORTS_PER_FILE} reports each...")

# Loop through the list of all reports in chunks
file_counter = 1
for i in range(0, len(all_reports), REPORTS_PER_FILE):
    # Get the slice/chunk of reports for this file
    report_chunk = all_reports[i : i + REPORTS_PER_FILE]
    
    # Define the output filename
    output_filename = f"{OUTPUT_PREFIX}_{file_counter}.txt"
    
    # Write this chunk to a new file
    try:
        with open(output_filename, 'w', encoding='utf-8') as out_f:
            # Join all reports in the chunk and write them at once
            out_f.write("".join(report_chunk))
            
        print(f"-> Created '{output_filename}' with {len(report_chunk)} reports.")
        file_counter += 1
    except Exception as e:
        print(f"An error occurred while writing {output_filename}: {e}")

print("\nSplitting complete. ✨")