from flickr.flickr import FolderToSync, FlickrSync
import argparse
import os
import warnings, exif
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"exif\._image")

parser = argparse.ArgumentParser(description="A script to upload photos to Flickr.")
parser.add_argument("--folder", type=str, required=False, help="Path to the folder containing files to upload.")
parser.add_argument("--folders", type=str, required=False, help="Path to the folder containing files to upload.")
parser.add_argument("--api_key", type=str, required=False, default="", help="Flickr API key.")
parser.add_argument("--api_secret", type=str, required=False, default="", help="Flickr API secret.")
parser.add_argument("--public", type=int, choices=[0, 1], default=0, help="Set photo visibility (0: private, 1: public).")
parser.add_argument("--sync_folder", type=int, choices=[0, 1], default=0, help="Set photo visibility (0: private, 1: public).")
args = parser.parse_args()

read_photos = False
print(f"Using folder: {args.folders or args.folder or args.sync_folder}")


if args.sync_folder:
    folder_path = os.path.abspath(args.sync_folder)
    read_photos = True
    files = FolderToSync(folder_path=folder_path)
    fs = FlickrSync(api_key=args.api_key, api_secret=args.api_secret, number_of_sets=200, read_photos=read_photos, limit=1)
    files_to_upload: list[str] = []
    for on_disk_key, on_disk_value in files.file_names.items():
        if on_disk_key not in fs.all_photos_title:
            files_to_upload.append(on_disk_value)
    print(f"Number of files not in Flickr: {len(files_to_upload)}")
    fs.upload_photos_parallel(files=files_to_upload, cnt=5)

elif args.folder:
    folder_path = os.path.abspath(os.path.join("y:\\2025", args.folder))
    files = FolderToSync(folder_path=folder_path)
    fs = FlickrSync(api_key=args.api_key, api_secret=args.api_secret, number_of_sets=200, read_photos=read_photos, limit=1)
    print(f"Number of files in folder: {len(files.files)}")
    fs.upload_photos_parallel(files=files.files, cnt=5)

elif args.folders:
    files_by_folder: dict[str, FolderToSync] = {}
    for folder in args.folders.split(","):
        folder_path = os.path.abspath(os.path.join("y:\\2025", folder))
        print(f"Processing folder: {folder_path}")
        files_by_folder.update({folder: FolderToSync(folder_path=folder_path)})

    files_to_upload: list[str] = []
    for files in files_by_folder.values():
        print(f"Processing folder: {files.folder_path} with {len(files.files)} files")
        for on_disk_key, on_disk_value in files.file_names.items():
            files_to_upload.append(on_disk_value)
    print(f"Number of files in folders: {len(files_to_upload)}")
    fs = FlickrSync(api_key=args.api_key, api_secret=args.api_secret, number_of_sets=200, read_photos=read_photos, limit=1)
    fs.upload_photos_parallel(files=files_to_upload, cnt=1)
