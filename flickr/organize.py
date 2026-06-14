import shutil
from datetime import datetime
from pathlib import Path


def organize_files_by_date(source_folder: str) -> None:
    source_path = Path(source_folder)

    if not source_path.exists():
        print(f"Error: Folder '{source_folder}' does not exist")
        return

    if not source_path.is_dir():
        print(f"Error: '{source_folder}' is not a directory")
        return

    files = [f for f in source_path.iterdir() if f.is_file()]

    if not files:
        print(f"No files found in '{source_folder}'")
        return

    print(f"Found {len(files)} file(s) to organize")

    for file_path in files:
        create_time = file_path.stat().st_birthtime if hasattr(file_path.stat(), "st_birthtime") else file_path.stat().st_mtime
        date_folder_name = datetime.fromtimestamp(create_time).strftime("%Y_%m_%d")
        date_folder_path = source_path / date_folder_name
        date_folder_path.mkdir(exist_ok=True)
        destination_path = date_folder_path / file_path.name
        shutil.move(str(file_path), str(destination_path))
        print(f"Moved: {file_path.name} -> {date_folder_name}/")
