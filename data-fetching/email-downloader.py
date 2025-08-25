import os
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm import tqdm
from docx2pdf import convert

# --- 1. CUSTOMIZE YOUR SETTINGS ---
# Search query for Gmail. This now looks for .doc and .docx files.
SEARCH_QUERY = 'has:attachment (filename:doc OR filename:docx)'

# The folder on your computer where files will be downloaded.
DOWNLOAD_DIR = r'./Files'

# List of keywords to look for in the attachment's filename (case-insensitive).
# Only attachments with a filename containing one of these words will be downloaded.
BODY_PART_KEYWORDS = ['thorax', 'brain']

# Set to True if you want to delete the original .doc/.docx file after a successful PDF conversion.
DELETE_SOURCE_DOC_AFTER_CONVERSION = True
# ------------------------------------


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    """Authenticates, searches, filters, downloads, and converts documents."""
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
                    
                    # Check if the part is a doc/docx file
                    is_document = filename.lower().endswith(('.doc', '.docx'))
                    if is_document:
                        # --- THIS IS THE DEBUG LINE ---
                        # It prints every doc/docx filename the script finds, before filtering.
                        tqdm.write(f"  [DEBUG] Found document: '{filename}'")
                        
                        # --- FEATURE: Filename Keyword Filtering ---
                        contains_keyword = any(keyword.lower() in filename.lower() for keyword in BODY_PART_KEYWORDS)

                        if contains_keyword:
                            source_doc_path = os.path.join(DOWNLOAD_DIR, filename)
                            final_pdf_path = os.path.splitext(source_doc_path)[0] + '.pdf'

                            # --- FEATURE: Continuation / Resumability ---
                            if os.path.exists(final_pdf_path):
                                continue

                            # Download the DOC file
                            attachment_id = part['body'].get('attachmentId')
                            attachment = service.users().messages().attachments().get(
                                userId='me', messageId=msg['id'], id=attachment_id
                            ).execute()
                            
                            file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                            with open(source_doc_path, 'wb') as f:
                                f.write(file_data)
                            
                            # --- FEATURE: Convert DOC to PDF ---
                            tqdm.write(f"    Downloaded '{filename}'. Converting to PDF...")
                            convert(source_doc_path, final_pdf_path)
                            tqdm.write(f"    ✅ Success: Converted and saved '{os.path.basename(final_pdf_path)}'.")

                            # # --- FEATURE: Optional Cleanup ---
                            # if DELETE_SOURCE_DOC_AFTER_CONVERSION:
                            #     os.remove(source_doc_path)
                            #     tqdm.write(f"    🗑️ Deleted source file: '{filename}'.")

            except Exception as e:
                tqdm.write(f"  ❌ Error processing message {msg['id']}: {e}")

    except HttpError as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()