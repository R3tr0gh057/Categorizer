import os
import fitz  # PyMuPDF
import time

# --- CONFIGURATION ---
# IMPORTANT: Update these paths to your actual folder locations
REPORTS_FOLDER = r"C:\path\to\unmatched_reports"
MAIN_FOLDER = r"C:\path\to\matched_reports"

# The phrases to search for, in order of priority
SENTENCE_PHRASE = "All on portal venous phase of CT abdomen, <3mm slice thickness"
PHRASE_CT = "CT abdomen"
PHRASE_VENOUS = "venous phase"

OUTPUT_FILE = "output.txt"
# --- END CONFIGURATION ---

def analyze_pdf(pdf_path):
    """
    Analyzes a PDF for different phrase combinations.
    Returns a category and relevant data based on what is found.
    """
    try:
        full_text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                full_text += page.get_text("text")

        # Priority 1: Check for the full sentence
        if SENTENCE_PHRASE in full_text:
            return "sentence", None # Stop if the highest priority match is found

        # Priority 2: Check for both individual phrases
        has_ct = PHRASE_CT in full_text
        has_venous = PHRASE_VENOUS in full_text

        if has_ct and has_venous:
            return "both", None # Stop if the second priority match is found

        # Priority 3 & 4: Check for individual phrases
        individual_matches = []
        if has_ct:
            individual_matches.append("ct_abdomen")
        if has_venous:
            individual_matches.append("venous_phase")
        
        if individual_matches:
            return "individual", individual_matches

    except Exception as e:
        print(f"-> ERROR: Could not process file '{os.path.basename(pdf_path)}'. Reason: {e}")
        return "error", None

    return "none", None


def main():
    """Main function to run the PDF search and save the results."""
    print("--- PDF Search Script Initialized with Multi-Tiered Logic ---")
    start_time = time.time()

    # Initialize lists for each category
    matches = {
        "sentence": [],
        "both": [],
        "venous_phase": [],
        "ct_abdomen": []
    }

    # Step 1: Gather all potential PDF files (simplified for clarity)
    print("Searching for all PDF files...")
    all_pdfs = []
    for folder_path in [REPORTS_FOLDER, MAIN_FOLDER]:
        if os.path.isdir(folder_path):
            for dirpath, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    if filename.lower().endswith('.pdf'):
                        all_pdfs.append(os.path.join(dirpath, filename))
        else:
            print(f"Warning: Directory not found: {folder_path}")

    if not all_pdfs:
        print("\nNo PDF files found in the specified directories. Exiting.")
        return
        
    total_files = len(all_pdfs)
    print(f"\nFound a total of {total_files} PDF(s) to scan.")
    print("--- Starting Detailed Scan ---")

    # Step 2: Analyze each PDF with detailed logging
    for i, pdf_path in enumerate(all_pdfs, 1):
        print(f"[{i}/{total_files}] Scanning: {pdf_path}")
        
        category, data = analyze_pdf(pdf_path)
        
        if category == "sentence":
            print(f"-> STATUS: FOUND full sentence.")
            matches["sentence"].append(pdf_path)
        elif category == "both":
            print(f"-> STATUS: FOUND both '{PHRASE_CT}' and '{PHRASE_VENOUS}'.")
            matches["both"].append(pdf_path)
        elif category == "individual":
            log_msg = "-> STATUS: Found individual phrase(s): " + ", ".join(data)
            print(log_msg)
            if "ct_abdomen" in data:
                matches["ct_abdomen"].append(pdf_path)
            if "venous_phase" in data:
                matches["venous_phase"].append(pdf_path)
        elif category == "none":
            print("-> STATUS: No target phrases found.")
            
    # Step 3: Save the results to the output file
    print(f"\n--- Scan Complete ---")
    total_matches = sum(len(v) for v in matches.values())
    print(f"Found {total_matches} total matches across all categories.")
    
    try:
        with open(OUTPUT_FILE, 'w') as f:
            if not any(matches.values()):
                f.write("No matching PDFs were found for any category.\n")
            else:
                f.write("--- Full Sentence Matches ---\n")
                if matches["sentence"]:
                    f.write("\n".join(matches["sentence"]) + "\n\n")
                else:
                    f.write("None\n\n")
                
                f.write(f"--- Matches with Both '{PHRASE_CT}' and '{PHRASE_VENOUS}' ---\n")
                if matches["both"]:
                    f.write("\n".join(matches["both"]) + "\n\n")
                else:
                    f.write("None\n\n")

                f.write(f"--- Matches with '{PHRASE_VENOUS}' ---\n")
                if matches["venous_phase"]:
                    f.write("\n".join(matches["venous_phase"]) + "\n\n")
                else:
                    f.write("None\n\n")
                
                f.write(f"--- Matches with '{PHRASE_CT}' ---\n")
                if matches["ct_abdomen"]:
                    f.write("\n".join(matches["ct_abdomen"]) + "\n")
                else:
                    f.write("None\n")

        print(f"Results successfully saved to '{OUTPUT_FILE}'")
    except IOError as e:
        print(f"Error: Could not write to output file '{OUTPUT_FILE}'. Reason: {e}")

    end_time = time.time()
    print(f"--- Script finished in {end_time - start_time:.2f} seconds ---")


if __name__ == "__main__":
    main()