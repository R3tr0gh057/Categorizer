import os
import argparse
import logging
from tqdm import tqdm
import dicom2nifti

# --- Setup Logging ---
# Configure logging to provide clear, timestamped feedback in the terminal.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def convert_dicom_to_nifti(input_dir, output_dir, overwrite=False):
    """
    Scans an input directory for subdirectories (each containing a DICOM series),
    and converts each series into a NIfTI file in the output directory.

    Args:
        input_dir (str): The path to the directory containing patient/scan subfolders.
        output_dir (str): The path to the directory where NIfTI files will be saved.
        overwrite (bool): If True, existing NIfTI files will be reconverted and overwritten.
    """
    # Ensure the output directory exists
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
    except OSError as e:
        logging.error(f"Failed to create output directory {output_dir}: {e}")
        return

    # Find all subdirectories in the input directory
    # We assume each subdirectory is a separate DICOM series
    try:
        dicom_series_dirs = [d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))]
        if not dicom_series_dirs:
            logging.warning(f"No subdirectories found in {input_dir}. Nothing to convert.")
            return
    except FileNotFoundError:
        logging.error(f"Input directory not found: {input_dir}")
        return

    logging.info(f"Found {len(dicom_series_dirs)} potential DICOM series to process.")

    # --- Main Conversion Loop ---
    # Use tqdm to create a progress bar for the conversion process.
    for series_dir_name in tqdm(dicom_series_dirs, desc="Overall Progress"):
        dicom_source_path = os.path.join(input_dir, series_dir_name)
        nifti_output_filename = f"{series_dir_name}.nii.gz"
        nifti_output_path = os.path.join(output_dir, nifti_output_filename)

        tqdm.write(f"\nProcessing: {dicom_source_path}") # tqdm.write is thread-safe for progress bars

        # --- Resumability Check ---
        # Skip conversion if the file already exists and overwrite is False.
        if os.path.exists(nifti_output_path) and not overwrite:
            tqdm.write(f"SKIPPING: Output file already exists: {nifti_output_path}")
            continue

        # --- Error Handling ---
        # Wrap the conversion in a try...except block to handle potential errors gracefully.
        try:
            # The core conversion function
            dicom2nifti.dicom_series_to_nifti(dicom_source_path, nifti_output_path, reorient_nifti=True)
            tqdm.write(f"SUCCESS: Converted '{series_dir_name}' to '{nifti_output_filename}'")
        except dicom2nifti.exceptions.ConversionError as e:
            tqdm.write(f"ERROR: Failed to convert {series_dir_name}. Reason: {e}")
            logging.error(f"Could not convert {dicom_source_path}: {e}")
        except Exception as e:
            tqdm.write(f"UNEXPECTED ERROR: An unknown error occurred for {series_dir_name}. Reason: {e}")
            logging.error(f"An unexpected error occurred for {dicom_source_path}: {e}")

    logging.info("Conversion process finished.")


if __name__ == "__main__":
    # --- Command-Line Argument Parsing ---
    # Makes the script user-friendly and configurable from the terminal.
    parser = argparse.ArgumentParser(
        description="Convert DICOM series directories to NIfTI files.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "input_dir",
        type=str,
        help="Path to the root directory containing DICOM series subfolders."
    )
    parser.add_argument(
        "output_dir",
        type=str,
        help="Path to the directory where NIfTI files will be saved."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true", # This makes it a flag, e.g., --overwrite
        help="If set, overwrite existing NIfTI files in the output directory."
    )

    args = parser.parse_args()

    # Run the main function with the provided arguments
    convert_dicom_to_nifti(args.input_dir, args.output_dir, args.overwrite)