import os  
import io
from collections import Counter
import json 
import sys 
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                print("="*80)
                print("ERROR: 'credentials.json' not found.")
                print("This file is required to authorize this script with Google Drive.")
                print("\nPlease follow these steps to generate it:")
                print("1. Go to the Google Cloud Console: https://console.cloud.google.com/")
                print("2. Create a new project or select an existing one.")
                print("3. In the search bar, find and enable the 'Google Drive API'.")
                print("4. Go to 'APIs & Services' -> 'Credentials'.")
                print("5. Click '+ CREATE CREDENTIALS' and select 'OAuth client ID'.")
                print("6. If prompted, configure the consent screen (select 'External' user type).")
                print("7. For 'Application type', choose 'Desktop app' and give it a name.")
                print("8. Click 'Create'. A window will pop up with your credentials.")
                print("9. Click 'DOWNLOAD JSON', save the file, rename it to 'credentials.json',")
                print("   and place it in the same directory as this script.")
                print("="*80)
                sys.exit(1) 
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def download_folder_recursively(service, folder_id, local_path, files_metadata):
    
    if not os.path.exists(local_path):
        os.makedirs(local_path)

    # --- Define Google Docs MIME types and their export formats ---
    export_mimetypes = {
        'application/vnd.google-apps.document': {
            'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'extension': '.docx'
        },
        'application/vnd.google-apps.spreadsheet': {
            'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'extension': '.xlsx'
        },
        'application/vnd.google-apps.presentation': {
            'mimeType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'extension': '.pptx'
        }
    }

    page_token = None
    while True:
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="nextPageToken, files(id, name, mimeType, webViewLink)",
            pageToken=page_token
        ).execute()
        
        items = results.get('files', [])

        for item in items:
            item_name = item.get('name')
            item_id = item.get('id')
            item_mimetype = item.get('mimeType')
            item_link = item.get('webViewLink')

            if item_mimetype == 'application/vnd.google-apps.folder':
                subfolder_path = os.path.join(local_path, item_name)
                print(f"Entering subfolder: {item_name}")
                download_folder_recursively(service, item_id, subfolder_path, files_metadata)
            
            elif item_mimetype in export_mimetypes:
                export_details = export_mimetypes[item_mimetype]
                export_mimetype = export_details['mimeType']
                export_extension = export_details['extension']
                
                new_filename = item_name + export_extension
                current_local_path = os.path.join(local_path, new_filename)
                
                print(f"  Exporting: '{item_name}' as '{new_filename}'")
                request = service.files().export_media(fileId=item_id, mimeType=export_mimetype)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                with open(current_local_path, 'wb') as f:
                    f.write(fh.getvalue())
                
                files_metadata[item_id] = {
                    'filename': new_filename,
                    'link': item_link,
                    'local_path': current_local_path
                }

            else:
                current_local_path = os.path.join(local_path, item_name)
                print(f"  Downloading: {item_name}")
                request = service.files().get_media(fileId=item_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                with open(current_local_path, 'wb') as f:
                    f.write(fh.getvalue())
                
                files_metadata[item_id] = {
                    'filename': item_name,
                    'link': item_link,
                    'local_path': current_local_path
                }
        
        page_token = results.get('nextPageToken', None)
        if page_token is None:
            break


def main():
    try:
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        
        folder_input = input("Please enter the Google Drive folder ID or URL: ")
        if not folder_input:
            print("Error: A folder ID or URL is required. Exiting.")
            return

        if "folders/" in folder_input:
            try:
                # Splits the URL using '/folders/' as a divider and takes the second part (the ID)
                folder_id = folder_input.split('/folders/')[1].split('?')[0]
            except IndexError:
                print("Error: Could not extract folder ID from the URL.")
                return
        else:
            # If it's not a URL, assume the input is the ID itself
            folder_id = folder_input

        folder_details = service.files().get(fileId=folder_id, fields='name').execute()
        folder_name = folder_details.get('name', 'Finance')
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        root_download_path = f"{timestamp}-{folder_name}"
        
        print(f"Starting download process. Files will be saved in: '{root_download_path}'")
        
        files_metadata = {}
        download_folder_recursively(service, folder_id, root_download_path, files_metadata)

        if files_metadata:
            metadata_filepath = os.path.join(root_download_path, 'files_metadata.json')
            with open(metadata_filepath, 'w') as f:
                json.dump(files_metadata, f, indent=4)
            print(f"\nDownload complete. All metadata saved to {metadata_filepath}")
        else:
            print("\nNo files were found to download.")

    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        if "invalid" in str(error).lower():
             print("Hint: Please ensure the Folder ID is correct and you have at least 'Viewer' permissions.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
