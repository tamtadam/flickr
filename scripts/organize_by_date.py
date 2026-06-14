import os
import sys

from flickr.organize import organize_files_by_date


if __name__ == "__main__":
    folder = os.environ.get("ORGANIZE_FOLDER") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not folder:
        print("Usage: python organize_by_date.py <folder_path>")
        sys.exit(1)
    organize_files_by_date(folder)
