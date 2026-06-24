import argparse

from flickr.upload_folder import sync_folder, upload_multiple_folders, upload_single_folder


parser = argparse.ArgumentParser(description="A script to upload photos to Flickr.")
parser.add_argument("--folder", type=str, required=False, help="Folder name under the upload root.")
parser.add_argument("--folders", type=str, required=False, help="Comma-separated folder names under the upload root.")
parser.add_argument("--sync_folder", type=str, required=False, default="", help="Absolute folder path to sync.")
parser.add_argument("--api_key", type=str, required=False, default="", help="Flickr API key.")
parser.add_argument("--api_secret", type=str, required=False, default="", help="Flickr API secret.")
parser.add_argument("--upload_failed", type=bool, required=False, default=False, help="Also retry files in FAILED subfolders.")
parser.add_argument("--year_set", type=str, required=False, default="__2026__", help="Flickr set name used as year tag.")
parser.add_argument("--public", type=int, choices=[0, 1], default=0, help="(unused, kept for backward compat)")
args = parser.parse_args()

print(f"Using: {args.folders or args.folder or args.sync_folder}")

if args.sync_folder:
    sync_folder(args.sync_folder, args.api_key, args.api_secret, args.upload_failed, args.year_set)
elif args.folder:
    upload_single_folder(args.folder, args.api_key, args.api_secret, args.upload_failed, year_set=args.year_set)
elif args.folders:
    upload_multiple_folders(args.folders.split(","), args.api_key, args.api_secret, args.upload_failed, year_set=args.year_set)
