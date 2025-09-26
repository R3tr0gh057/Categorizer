import os
import fitz  # The PyMuPDF library
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue

# --- DEFAULT CONFIGURATION ---
DEFAULT_SEARCH_TERMS = [
    "acute diverticulitis",
    "acute cholecystitis",
    "acute pancreas",
    "acute pancreatitis",
    "appendicite",
    "appendicitis"
]
OUTPUT_FILE = "search_report_results.txt"

# --- BACKEND LOGIC (Modified to report progress) ---
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def get_pdf_paths(folders_to_scan, progress_queue):
    """Scans folders to find all PDF paths, reporting progress via a queue."""
    pdf_paths = []
    progress_queue.put(("log", "Phase 1: Discovering PDF files..."))
    for folder in folders_to_scan:
        if not os.path.isdir(folder):
            progress_queue.put(("log", f"Warning: Folder not found, skipping: {folder}"))
            continue
        progress_queue.put(("log", f"Scanning folder: {folder}"))
        for root, _, files in os.walk(folder, topdown=True):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_paths.append(os.path.join(root, file))
    progress_queue.put(("log", f"Discovery complete. Found {len(pdf_paths)} PDF files."))
    return pdf_paths

def extract_text_from_pdf(pdf_path):
    try:
        with fitz.open(pdf_path) as doc:
            return " ".join(page.get_text("text").lower() for page in doc)
    except Exception as e:
        logging.error(f"Failed to read or process {pdf_path}: {e}")
        return None

def find_and_process_pdfs(all_pdfs, terms_with_acute, terms_without_acute, progress_queue):
    """Processes a list of PDFs, applying positive match logic and reporting progress."""
    progress_queue.put(("log", "\nPhase 2: Analyzing report content..."))
    
    exact_match_counts = {term: 0 for term in terms_with_acute}
    partial_match_counts = {term: 0 for term in terms_without_acute}
    exact_match_files = {term: set() for term in terms_with_acute}
    partial_match_files = {term: set() for term in terms_without_acute}
    
    total_files = len(all_pdfs)
    for i, pdf_path in enumerate(all_pdfs):
        # Update progress bar and log the current file
        progress_value = int(((i + 1) / total_files) * 100)
        progress_queue.put(("progress", progress_value))
        progress_queue.put(("log", f"Analyzing [{i+1}/{total_files}]: {os.path.basename(pdf_path)}"))
        
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
    # ... (Reporting logic is unchanged) ...
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

# --- INTERACTIVE GUI CLASS (UPDATED) ---
class PdfSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Report Analyzer")
        self.root.geometry("800x600")

        self.reports_folder = ""
        self.main_folder = ""
        self.progress_queue = queue.Queue()

        # --- Main Layout Frames ---
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = tk.Frame(main_frame, width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        right_frame = tk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- Left Panel: Controls ---
        folder_frame = tk.Frame(left_frame, relief=tk.RIDGE, borderwidth=2)
        folder_frame.pack(fill=tk.X, pady=5)
        
        self.reports_label = tk.Label(folder_frame, text="Unmatched Reports Folder: Not selected", wraplength=380)
        self.reports_label.pack(pady=5)
        self.reports_button = tk.Button(folder_frame, text="Select Folder with PDFs", command=self.select_reports_folder)
        self.reports_button.pack(pady=(0, 5))

        self.main_label = tk.Label(folder_frame, text="Matched Reports Folder: Not selected", wraplength=380)
        self.main_label.pack(pady=5)
        self.main_button = tk.Button(folder_frame, text="Select Folder with Patient Folders", command=self.select_main_folder)
        self.main_button.pack(pady=(0, 10))
        
        terms_frame = tk.Frame(left_frame, relief=tk.RIDGE, borderwidth=2)
        terms_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        tk.Label(terms_frame, text="Search Terms:").pack(anchor=tk.W, padx=5, pady=5)
        
        list_frame = tk.Frame(terms_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.terms_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        for term in DEFAULT_SEARCH_TERMS: self.terms_listbox.insert(tk.END, term)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.terms_listbox.yview)
        self.terms_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terms_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(terms_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        self.add_entry = tk.Entry(button_frame)
        self.add_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.add_button = tk.Button(button_frame, text="Add", command=self.add_term)
        self.add_button.pack(side=tk.LEFT, padx=5)
        self.remove_button = tk.Button(button_frame, text="Remove", command=self.remove_term)
        self.remove_button.pack(side=tk.LEFT)
        
        # --- Right Panel: Log ---
        tk.Label(right_frame, text="Live Log").pack()
        self.log_text = scrolledtext.ScrolledText(right_frame, state='disabled', wrap=tk.WORD, font=("Courier New", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Bottom Panel: Actions & Status ---
        action_frame = tk.Frame(root)
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.run_button = tk.Button(action_frame, text="Start Analysis", command=self.start_analysis_thread, font=("Helvetica", 12, "bold"))
        self.run_button.pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(action_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, expand=True, pady=5)

        self.status_label = tk.Label(root, text="Status: Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.check_queue()

    def add_log_message(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def check_queue(self):
        """Periodically check the queue for messages from the worker thread."""
        try:
            while True:
                message_type, value = self.progress_queue.get_nowait()
                if message_type == "log":
                    self.add_log_message(value)
                elif message_type == "progress":
                    self.progress_bar['value'] = value
                elif message_type == "complete":
                    self.analysis_complete()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)
    
    def select_reports_folder(self):
        folder = filedialog.askdirectory(title="Select folder with PDF reports")
        if folder: self.reports_folder = folder; self.reports_label.config(text=f"Unmatched Reports Folder: {folder}")

    def select_main_folder(self):
        folder = filedialog.askdirectory(title="Select folder with patient subfolders")
        if folder: self.main_folder = folder; self.main_label.config(text=f"Matched Reports Folder: {folder}")

    def add_term(self):
        new_term = self.add_entry.get().strip().lower()
        if new_term and new_term not in self.terms_listbox.get(0, tk.END):
            self.terms_listbox.insert(tk.END, new_term); self.add_entry.delete(0, tk.END)

    def remove_term(self):
        for index in reversed(self.terms_listbox.curselection()): self.terms_listbox.delete(index)

    def start_analysis_thread(self):
        if not self.reports_folder and not self.main_folder:
            messagebox.showerror("Error", "Please select at least one folder to scan.")
            return
        
        self.run_button.config(state=tk.DISABLED)
        self.log_text.config(state='normal'); self.log_text.delete('1.0', tk.END); self.log_text.config(state='disabled')
        self.progress_bar['value'] = 0
        
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def run_analysis(self):
        folders_to_scan = [f for f in [self.reports_folder, self.main_folder] if f]
        all_pdfs = get_pdf_paths(folders_to_scan, self.progress_queue)
        
        search_terms = list(self.terms_listbox.get(0, tk.END))
        terms_with_acute = sorted([term for term in search_terms])
        terms_without_acute = sorted(list(set([term.replace('acute ', '') for term in terms_with_acute])))
        
        exact_files, partial_files, exact_counts, partial_counts = find_and_process_pdfs(
            all_pdfs, terms_with_acute, terms_without_acute, self.progress_queue
        )
        
        write_report(exact_files, partial_files, exact_counts, partial_counts, terms_with_acute, terms_without_acute)
        self.progress_queue.put(("complete", None))

    def analysis_complete(self):
        self.status_label.config(text=f"Status: Complete! Report saved to {OUTPUT_FILE}")
        messagebox.showinfo("Success", f"Analysis complete!\nReport saved to '{os.path.abspath(OUTPUT_FILE)}'")
        self.run_button.config(state=tk.NORMAL)
        self.progress_bar['value'] = 100

if __name__ == "__main__":
    root = tk.Tk()
    app = PdfSearchApp(root)
    root.mainloop()