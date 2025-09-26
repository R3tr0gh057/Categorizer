import os
import fitz  # The PyMuPDF library
from tqdm import tqdm
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading

# --- DEFAULT CONFIGURATION ---
# These will be the terms that load when the app starts
DEFAULT_SEARCH_TERMS = [
    "acute diverticulitis",
    "acute cholecystitis",
    "acute pancreas",
    "acute pancreatitis",
    "appendicite",
    "appendicitis"
]
OUTPUT_FILE = "search_report_results.txt"

# --- BACKEND LOGIC (UNCHANGED) ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def stream_pdfs(folders_to_scan):
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            continue
        for root, _, files in os.walk(folder, topdown=True):
            for file in files:
                if file.lower().endswith('.pdf'):
                    yield os.path.join(root, file)

def extract_text_from_pdf(pdf_path):
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text").lower() for page in doc)
    except Exception as e:
        logging.error(f"Failed to read or process {pdf_path}: {e}")
        return None

def find_and_process_pdfs(all_pdfs, terms_with_acute, terms_without_acute, update_status_callback):
    exact_match_counts = {term: 0 for term in terms_with_acute}
    partial_match_counts = {term: 0 for term in terms_without_acute}
    exact_match_files = {term: set() for term in terms_with_acute}
    partial_match_files = {term: set() for term in terms_without_acute}
    
    total_files = len(all_pdfs)
    for i, pdf_path in enumerate(all_pdfs):
        update_status_callback(f"Status: Analyzing file {i+1}/{total_files}...")
        full_text = extract_text_from_pdf(pdf_path)
        if full_text:
            for term in terms_with_acute:
                negative_phrase = f"no evidence of {term}"
                if term in full_text and negative_phrase not in full_text:
                    exact_match_counts[term] += 1
                    exact_match_files[term].add(pdf_path)
            for term in terms_without_acute:
                negative_phrase = f"no evidence of {term}"
                if term in full_text and negative_phrase not in full_text:
                    partial_match_counts[term] += 1
                    partial_match_files[term].add(pdf_path)
    return exact_match_files, partial_match_files, exact_match_counts, partial_match_counts

def write_report(exact_files_dict, partial_files_dict, exact_counts, partial_counts, terms_with_acute, terms_without_acute):
    report_lines = ["--- Search Results ---"]
    # Report for List 1
    report_lines.extend([f"\n{'='*55}", "## 1. List 1: Reports with original terms", f"{'='*55}", "### Individual Term Counts:"])
    total_exact_files = set()
    for term in sorted(exact_counts.keys()):
        count = exact_counts[term]
        report_lines.append(f"  - {term:<25}: {count} reports")
        total_exact_files.update(exact_files_dict.get(term, set()))
    report_lines.extend([f"\n### Total Unique Reports in this Category: {len(total_exact_files)}", "--- File List ---"])
    for term in terms_with_acute:
        files = sorted(list(exact_files_dict.get(term, set())))
        if files:
            report_lines.append(f"\n#### Files containing '{term}':")
            report_lines.extend(f"- {file_path}" for file_path in files)

    # Report for List 2
    report_lines.extend([f"\n{'='*55}", "## 2. List 2: Reports with terms excluding 'acute'", f"{'='*55}", "### Individual Term Counts:"])
    total_partial_files = set()
    for term in sorted(partial_counts.keys()):
        count = partial_counts[term]
        report_lines.append(f"  - {term:<25}: {count} reports")
        total_partial_files.update(partial_files_dict.get(term, set()))
    report_lines.extend([f"\n### Total Unique Reports in this Category: {len(total_partial_files)}", "--- File List ---"])
    for term in terms_without_acute:
        files = sorted(list(partial_files_dict.get(term, set())))
        if files:
            report_lines.append(f"\n#### Files containing '{term}':")
            report_lines.extend(f"- {file_path}" for file_path in files)
    report_lines.append("\n--- End of Report ---")
    
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_lines))
        return True
    except Exception as e:
        logging.error(f"Could not write report to file: {e}")
        return False

# --- NEW INTERACTIVE GUI CLASS ---
class PdfSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Report Analyzer")
        self.root.geometry("600x550")

        self.reports_folder = ""
        self.main_folder = ""

        # --- Folder Selection Frame ---
        folder_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
        folder_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.reports_label = tk.Label(folder_frame, text="Unmatched Reports Folder: Not selected", wraplength=580)
        self.reports_label.pack(pady=5)
        self.reports_button = tk.Button(folder_frame, text="Select Folder with PDFs", command=self.select_reports_folder)
        self.reports_button.pack(pady=(0, 5))

        self.main_label = tk.Label(folder_frame, text="Matched Reports Folder: Not selected", wraplength=580)
        self.main_label.pack(pady=5)
        self.main_button = tk.Button(folder_frame, text="Select Folder with Patient Folders", command=self.select_main_folder)
        self.main_button.pack(pady=(0, 10))

        # --- Search Term Management Frame ---
        terms_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
        terms_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(terms_frame, text="Search Terms:").pack(anchor=tk.W, padx=5, pady=5)
        
        list_frame = tk.Frame(terms_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.terms_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        for term in DEFAULT_SEARCH_TERMS:
            self.terms_listbox.insert(tk.END, term)
        
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.terms_listbox.yview)
        self.terms_listbox.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terms_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Add/Remove Buttons Frame ---
        button_frame = tk.Frame(terms_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.add_entry = tk.Entry(button_frame)
        self.add_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        
        self.add_button = tk.Button(button_frame, text="Add Term", command=self.add_term)
        self.add_button.pack(side=tk.LEFT, padx=5)
        
        self.remove_button = tk.Button(button_frame, text="Remove Selected", command=self.remove_term)
        self.remove_button.pack(side=tk.LEFT)
        
        # --- Action Frame ---
        self.run_button = tk.Button(root, text="Start Analysis", command=self.start_analysis_thread, font=("Helvetica", 12, "bold"))
        self.run_button.pack(pady=10)

        self.status_label = tk.Label(root, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def select_reports_folder(self):
        folder = filedialog.askdirectory(title="Select folder with PDF reports")
        if folder:
            self.reports_folder = folder
            self.reports_label.config(text=f"Unmatched Reports Folder: {self.reports_folder}")

    def select_main_folder(self):
        folder = filedialog.askdirectory(title="Select folder with patient subfolders")
        if folder:
            self.main_folder = folder
            self.main_label.config(text=f"Matched Reports Folder: {self.main_folder}")

    def add_term(self):
        new_term = self.add_entry.get().strip().lower()
        if new_term and new_term not in self.terms_listbox.get(0, tk.END):
            self.terms_listbox.insert(tk.END, new_term)
            self.add_entry.delete(0, tk.END)

    def remove_term(self):
        selected_indices = self.terms_listbox.curselection()
        # Iterate backwards to avoid index shifting issues
        for index in reversed(selected_indices):
            self.terms_listbox.delete(index)

    def update_status(self, message):
        self.status_label.config(text=message)

    def start_analysis_thread(self):
        if not self.reports_folder and not self.main_folder:
            messagebox.showerror("Error", "Please select at least one folder to scan.")
            return
        
        self.run_button.config(state=tk.DISABLED)
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def run_analysis(self):
        self.root.after(0, self.update_status, "Status: Discovering PDF files...")
        folders_to_scan = [f for f in [self.reports_folder, self.main_folder] if f]
        all_pdfs = list(stream_pdfs(folders_to_scan))
        
        self.root.after(0, self.update_status, f"Status: Found {len(all_pdfs)} files. This may take a while...")

        search_terms = list(self.terms_listbox.get(0, tk.END))
        terms_with_acute = sorted([term for term in search_terms])
        terms_without_acute = sorted(list(set([term.replace('acute ', '') for term in terms_with_acute])))
        
        exact_files, partial_files, exact_counts, partial_counts = find_and_process_pdfs(
            all_pdfs, terms_with_acute, terms_without_acute, lambda msg: self.root.after(0, self.update_status, msg)
        )
        
        write_report(exact_files_dict, partial_files_dict, exact_counts, partial_counts, terms_with_acute, terms_without_acute)
        
        self.root.after(0, self.update_status, f"Status: Complete! Report saved to {OUTPUT_FILE}")
        self.root.after(0, lambda: messagebox.showinfo("Success", f"Analysis complete!\nReport saved to '{os.path.abspath(OUTPUT_FILE)}'"))
        
        self.root.after(0, self.run_button.config, {'state': tk.NORMAL})

if __name__ == "__main__":
    root = tk.Tk()
    app = PdfSearchApp(root)
    root.mainloop()