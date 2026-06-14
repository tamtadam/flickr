#!/usr/bin/env python3
"""
Organize files in a folder by their creation date.
Files are moved to subfolders named YYYY_MM_DD based on file creation date.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path


def organize_files_by_date(source_folder):
    """
    Organize files in source_folder into subfolders by creation date.

    Args:
        source_folder (str): Path to the folder containing files to organize
    """
    source_path = Path(source_folder)

    if not source_path.exists():
        print(f"Error: Folder '{source_folder}' does not exist")
        return

    if not source_path.is_dir():
        print(f"Error: '{source_folder}' is not a directory")
        return

    # Get all files in the folder (not recursive)
    files = [f for f in source_path.iterdir() if f.is_file()]

    if not files:
        print(f"No files found in '{source_folder}'")
        return

    print(f"Found {len(files)} file(s) to organize")

    for file_path in files:
        # Get creation time (use modification time on Unix/Linux)
        create_time = file_path.stat().st_birthtime if hasattr(file_path.stat(), "st_birthtime") else file_path.stat().st_mtime

        # Format date as YYYY_MM_DD
        date_folder_name = datetime.fromtimestamp(create_time).strftime("%Y_%m_%d")
        date_folder_path = source_path / date_folder_name

        # Create date folder if it doesn't exist
        date_folder_path.mkdir(exist_ok=True)

        # Move file to date folder
        destination_path = date_folder_path / file_path.name
        shutil.move(str(file_path), str(destination_path))
        print(f"Moved: {file_path.name} -> {date_folder_name}/")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python organize_by_date.py <folder_path>")
        print("Example: python organize_by_date.py ./my_downloads")

    folder = os.environ.get("ORGANIZE_FOLDER", sys.argv[1] if len(sys.argv) > 1 else None)
    organize_files_by_date(folder)
