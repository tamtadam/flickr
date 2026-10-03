import os
import warnings
from pathlib import Path

from flickr.flickr import FilesInSet, FlickrSync, FolderToSync


warnings.filterwarnings("ignore", category=RuntimeWarning, module=r"exif\._image")

UPLOAD_ROOT = os.environ.get("UPLOAD_ROOT", None)
_VIDEO_EXTENSIONS = {".mp4", ".MP4", ".mov", ".MOV", ".avi", ".AVI"}


def _filter_conv_only(files: list[FilesInSet]) -> list[FilesInSet]:
    result = []
    for f in files:
        p = Path(f.full_path)
        if p.suffix in _VIDEO_EXTENSIONS or p.stem.endswith("_conv"):
            result.append(f)
    return result


def _print_file_sets(files: list[FilesInSet], year_set: str) -> None:
    for f in files:
        sets = [year_set] + f.sets
        print(f"  {f.filename}  →  {', '.join(sets)}")


def upload_single_folder(
    folder: str,
    api_key: str = "",
    api_secret: str = "",
    upload_failed: bool = False,
    upload_root: str = UPLOAD_ROOT,
    year_set: str = "__2026__",
    conv_only: bool = False,
) -> None:
    folder_path = os.path.abspath(folder)
    files = FolderToSync(folder_path=folder_path, upload_failed=upload_failed)
    to_upload = _filter_conv_only(files.files) if conv_only else files.files
    print(f"Number of files in folder: {len(to_upload)}")
    _print_file_sets(to_upload, year_set)
    fs = FlickrSync(api_key=api_key, api_secret=api_secret, number_of_sets=200, read_photos=False, limit=1, year_set=year_set)
    fs.upload_photos_parallel(files=to_upload, cnt=15)


def upload_multiple_folders(
    folders: list[str],
    api_key: str = "",
    api_secret: str = "",
    upload_failed: bool = False,
    upload_root: str = UPLOAD_ROOT,
    year_set: str = "__2026__",
    conv_only: bool = False,
) -> None:
    files_by_folder: dict = {}
    for folder in folders:
        folder_path = os.path.abspath(folder)
        print(f"Processing folder: {folder_path}")
        files_by_folder[folder] = FolderToSync(folder_path=folder_path, upload_failed=upload_failed)

    files_to_upload: list = []
    for files in files_by_folder.values():
        candidates = _filter_conv_only(files.files) if conv_only else list(files.file_names.values())
        print(f"Processing folder: {files.folder_path} with {len(candidates)} files")
        files_to_upload.extend(candidates)
    print(f"Number of files in folders: {len(files_to_upload)}")
    _print_file_sets(files_to_upload, year_set)
    fs = FlickrSync(api_key=api_key, api_secret=api_secret, number_of_sets=411, read_photos=False, limit=11, year_set=year_set)
    fs.upload_photos_parallel(files=files_to_upload, cnt=20)


def sync_folder(folder: str, api_key: str = "", api_secret: str = "", upload_failed: bool = False, year_set: str = "__2026__") -> None:
    fs = FlickrSync(api_key=api_key, api_secret=api_secret, number_of_sets=500, read_photos=True, limit=1, year_set=year_set)
    folder_path = os.path.abspath(folder)
    files = FolderToSync(folder_path=folder_path, upload_failed=upload_failed)
    files_to_upload: list = []
    for on_disk_key, on_disk_value in files.file_names.items():
        # Check against the year_set (primary set), not the folder name
        try:
            fs.all_photos_title_by_set.get(year_set, []).index(on_disk_key)
            print(f"File {on_disk_key} already exists in Flickr in set {year_set}, skipping upload.")
        except ValueError:
            files_to_upload.append(on_disk_value)
    print(f"Number of files not in Flickr: {len(files_to_upload)}")
    fs.upload_photos_parallel(files=files_to_upload, cnt=10)
