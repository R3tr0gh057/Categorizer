import os
import base64
import subprocess
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm

# --- 1. CUSTOMIZE YOUR SETTINGS ---
SEARCH_QUERY = 'has:attachment (filename:doc OR filename:docx)'
DOWNLOAD_DIR = r'D:\Projects2025\Categorizer\data-fetching\Files'
BODY_PART_KEYWORDS = ['brain', 'thorax', 'abdomen', 'pelvis', 'ct report']
DELETE_SOURCE_DOC_AFTER_CONVERSION = True
# ------------------------------------

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def convert_with_libreoffice(source_path, output_dir):
    """Converts a document to PDF using the LibreOffice command line."""
    try:
        # Command for LibreOffice conversion
        command = [
            "soffice", # The LibreOffice executable
            "--headless", # Run without opening the GUI
            "--convert-to", "pdf", # Specify the output format
            "--outdir", output_dir, # Specify the output directory
            source_path # The input file to convert
        ]
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        tqdm.write("  ❌ ERROR: 'soffice' command not found. Is LibreOffice installed and in your system's PATH?")
        return False
    except subprocess.CalledProcessError as e:
        tqdm.write(f"  ❌ ERROR: LibreOffice conversion failed for {os.path.basename(source_path)}. Error: {e.stderr.decode('utf-8', errors='ignore')}")
        return False

def main():
    """Authenticates, searches, filters, downloads, and converts documents using LibreOffice."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
            print(f"Created download directory: {DOWNLOAD_DIR}")

        service = build('gmail', 'v1', credentials=creds)
        result = service.users().messages().list(userId='me', q=SEARCH_QUERY).execute()
        messages = result.get('messages', [])

        if not messages:
            print("No messages found matching your query.")
            return

        print(f"Found {len(messages)} total messages with DOC/DOCX attachments. Filtering and processing now...")
        
        for msg in tqdm(messages, desc="Processing Emails"):
            try:
                txt = service.users().messages().get(userId='me', id=msg['id']).execute()
                
                for part in txt['payload']['parts']:
                    filename = part.get('filename')
                    if not filename:
                        continue
                    
                    is_document = filename.lower().endswith(('.doc', '.docx'))
                    contains_keyword = any(keyword.lower() in filename.lower() for keyword in BODY_PART_KEYWORDS)

                    if is_document and contains_keyword:
                        source_doc_path = os.path.join(DOWNLOAD_DIR, filename)
                        final_pdf_path = os.path.splitext(source_doc_path)[0] + '.pdf'

                        if os.path.exists(final_pdf_path):
                            continue

                        attachment_id = part['body'].get('attachmentId')
                        attachment = service.users().messages().attachments().get(
                            userId='me', messageId=msg['id'], id=attachment_id
                        ).execute()
                        
                        file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                        with open(source_doc_path, 'wb') as f:
                            f.write(file_data)
                        
                        tqdm.write(f"  Downloaded '{filename}'. Converting with LibreOffice...")
                        
                        # --- NEW HIGH-FIDELITY CONVERSION ---
                        success = convert_with_libreoffice(source_doc_path, DOWNLOAD_DIR)

                        if success:
                            tqdm.write(f"  ✅ Success: Converted and saved '{os.path.basename(final_pdf_path)}'.")
                            if DELETE_SOURCE_DOC_AFTER_CONVERSION:
                                os.remove(source_doc_path)
                                tqdm.write(f"  🗑️ Deleted source file: '{filename}'.")
                        else:
                            # Keep the source file if conversion fails
                            tqdm.write(f"  ⚠️ Kept source file '{filename}' due to conversion failure.")


            except Exception as e:
                tqdm.write(f"  ❌ Error processing message {msg['id']}: {e}")

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()