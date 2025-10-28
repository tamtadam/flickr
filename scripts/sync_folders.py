from flickr.flickr import FolderToSync, FlickrSync
import os
API_KEY = os.getenv("FLICKR_API_KEY", "")
API_SECRET = os.getenv("FLICKR_API_SECRET", "")
OAUTH_TOKEN = os.getenv("FLICKR_OAUTH_TOKEN", "")
OAUTH_TOKEN_SECRET = os.getenv("FLICKR_OAUTH_TOKEN_SECRET", "")

fs = FlickrSync(api_key=API_KEY, api_secret=API_SECRET, number_of_sets=200, read_photos=True, limit=1)
folders: list = [
    "y:\\2025\\",
]
files_by_folder: dict[str, FolderToSync] = {}
for folder in folders:
    files_by_folder.update({folder: FolderToSync(folder_path=folder)})

files: FolderToSync
files_not_in_flickr: list[str] = []
for files in files_by_folder.values():
    print(f"Processing folder: {files.folder_path} with {len(files.files)} files")
    for on_disk_key, on_disk_value in files.file_names.items():
        if on_disk_key not in fs.all_photos_title:
            files_not_in_flickr.append(on_disk_value)

fs.upload_photos_parallel(files=files_not_in_flickr, cnt=10)
