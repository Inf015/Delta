#!/usr/bin/env python3
"""
upload_to_drive.py — Sube un PDF a la carpeta del piloto en Google Drive.
Uso: python3 upload_to_drive.py /tmp/reporte.pdf "Oliver Infante" "1100292"
Output: DRIVE_PDF_LINK:https://... DRIVE_FOLDER_LINK:https://...
"""
import sys, json
from pathlib import Path

def upload(pdf_path, pilot_name, pilot_id):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    TOKEN = '/root/.config/gdrive/oauth_token.json'
    ROOT  = '1x-2bByARqKM1ZYdXW1Sn0zTkcyTToq4W'

    with open(TOKEN) as f: data = json.load(f)
    creds = Credentials(token=data['token'], refresh_token=data['refresh_token'],
        token_uri=data['token_uri'], client_id=data['client_id'],
        client_secret=data['client_secret'], scopes=data['scopes'])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        data['token'] = creds.token
        with open(TOKEN, 'w') as f: json.dump(data, f)

    svc = build('drive', 'v3', credentials=creds)
    folders = svc.files().list(
        q=f"'{ROOT}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields='files(id,name)').execute().get('files', [])
    folder = next((f for f in folders if pilot_id in f['name']), None)
    if not folder:
        folder = svc.files().create(body={
            'name': f'{pilot_id}_{pilot_name.replace(" ","")}',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [ROOT]}, fields='id').execute()

    up = svc.files().create(
        body={'name': Path(pdf_path).name, 'parents': [folder['id']]},
        media_body=MediaFileUpload(str(pdf_path), mimetype='application/pdf'),
        fields='id,webViewLink').execute()

    print(f"DRIVE_PDF_LINK:{up['webViewLink']}")
    print(f"DRIVE_FOLDER_LINK:https://drive.google.com/drive/folders/{folder['id']}")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Uso: upload_to_drive.py <pdf_path> <pilot_name> <pilot_id>")
        sys.exit(1)
    upload(sys.argv[1], sys.argv[2], sys.argv[3])
