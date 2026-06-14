import os
import warnings

from flickr.flickr import FlickrSync, FolderToSync


warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"exif\._image")

UPLOAD_ROOT = "/Volumes/photo/2026"


def upload_single_folder(folder: str, api_key: str = "", api_secret: str = "", upload_failed: bool = False) -> None:
    folder_path = os.path.abspath(os.path.join(UPLOAD_ROOT, folder))
    files = FolderToSync(folder_path=folder_path, upload_failed=upload_failed)
    fs = FlickrSync(api_key=api_key, api_secret=api_secret, number_of_sets=200, read_photos=False, limit=1)
    print(f"Number of files in folder: {len(files.files)}")
    fs.upload_photos_parallel(files=files.files, cnt=15)


def upload_multiple_folders(folders: list[str], api_key: str = "", api_secret: str = "", upload_failed: bool = False) -> None:
    files_by_folder: dict = {}
    for folder in folders:
        folder_path = os.path.abspath(os.path.join(UPLOAD_ROOT, folder))
        print(f"Processing folder: {folder_path}")
        files_by_folder[folder] = FolderToSync(folder_path=folder_path, upload_failed=upload_failed)

    files_to_upload: list = []
    for files in files_by_folder.values():
        print(f"Processing folder: {files.folder_path} with {len(files.files)} files")
        for on_disk_value in files.file_names.values():
            files_to_upload.append(on_disk_value)
    print(f"Number of files in folders: {len(files_to_upload)}")
    fs = FlickrSync(api_key=api_key, api_secret=api_secret, number_of_sets=411, read_photos=False, limit=11)
    fs.upload_photos_parallel(files=files_to_upload, cnt=20)


def sync_folder(folder: str, api_key: str = "", api_secret: str = "", upload_failed: bool = False) -> None:
    fs = FlickrSync(api_key=api_key, api_secret=api_secret, number_of_sets=500, read_photos=True, limit=1)
    folder_path = os.path.abspath(folder)
    files = FolderToSync(folder_path=folder_path, upload_failed=upload_failed)
    files_to_upload: list = []
    for on_disk_key, on_disk_value in files.file_names.items():
        first_set = on_disk_value.sets[0]
        try:
            fs.all_photos_title_by_set.get(first_set, []).index(on_disk_key)
            print(f"File {on_disk_key} already exists in Flickr in set {first_set}, skipping upload.")
        except ValueError:
            files_to_upload.append(on_disk_value)
    print(f"Number of files not in Flickr: {len(files_to_upload)}")
    fs.upload_photos_parallel(files=files_to_upload, cnt=10)
