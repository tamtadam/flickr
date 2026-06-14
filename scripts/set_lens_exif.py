import argparse
import sys

from flickr.exif import LENSES, MyExif


parser = argparse.ArgumentParser(description="Set lens EXIF on every image in a folder.")
parser.add_argument("--folder", type=str, required=True, help="Folder containing the images to modify.")
parser.add_argument(
    "--lens",
    type=str,
    required=True,
    choices=sorted(LENSES.keys()) + ["auto"],
    help="Lens preset key from LENSES, or 'auto' to pick per subfolder by name.",
)
args = parser.parse_args()

if args.lens == "auto":
    print(f"Auto mode: matching subfolders of {args.folder} against LENSES keys.")
    results = MyExif.apply_by_subfolder_names(args.folder)
    total = sum(len(v) for v in results.values())
    print(f"Done. {total} file(s) modified across {len(results)} subfolder(s).")
    sys.exit(0 if total else 1)

lens = LENSES[args.lens]
print(f"Applying '{lens.lens_model}' to folder: {args.folder}")

moved = MyExif(lens).apply_to_path(args.folder)
print(f"Done. {len(moved)} file(s) modified and moved one level up.")

sys.exit(0 if moved else 1)
