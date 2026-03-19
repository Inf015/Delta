#!/usr/bin/env python3
"""Sync CSV files from Google Drive lapdata/ folders to /mnt/carrera/"""
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import json, os, io

TOKEN = '/root/.config/gdrive/oauth_token.json'
FOLDERS = {
    'ac':  ('15HFvwfhwCzCtayhM8JlKraiQevLejJK1', '/mnt/carrera/ac'),
    'r3e': ('1hZGu3ZtHETDi_8AWt4kckoDeXt22ypcb',  '/mnt/carrera/r3e'),
}

with open(TOKEN) as f:
    data = json.load(f)
creds = Credentials(token=data['token'], refresh_token=data['refresh_token'],
    token_uri=data['token_uri'], client_id=data['client_id'],
    client_secret=data['client_secret'], scopes=data['scopes'])
if creds.expired:
    creds.refresh(Request())
    data['token'] = creds.token
    with open(TOKEN, 'w') as f:
        json.dump(data, f)

service = build('drive', 'v3', credentials=creds)

total_new = 0
for sim, (folder_id, local_dir) in FOLDERS.items():
    os.makedirs(local_dir, exist_ok=True)
    results = service.files().list(
        q=f"'{folder_id}' in parents and name contains '.csv' and trashed=false",
        orderBy='modifiedTime desc',
        pageSize=50,
        fields='files(id,name,modifiedTime)'
    ).execute()
    for f in results.get('files', []):
        dest = os.path.join(local_dir, f['name'])
        if os.path.exists(dest):
            continue
        print(f'  Descargando {sim}/{f["name"]}...')
        req = service.files().get_media(fileId=f['id'])
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        with open(dest, 'wb') as out:
            out.write(buf.getvalue())
        total_new += 1

print(f'Sync completo: {total_new} archivo(s) nuevo(s)')
