from importlib.resources import path
import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field, fields
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Union

from exif import Image


JPEG_EXTENSIONS = (".jpg", ".jpeg", ".JPG", ".JPEG")
EXIFTOOL_EXTENSIONS = (".ARW", ".CR2", ".NEF", ".DNG", ".TIFF", ".PNG", ".GIF", ".BMP")
IMAGE_EXTENSIONS = JPEG_EXTENSIONS + EXIFTOOL_EXTENSIONS


class ExiftoolTag(str, Enum):
    """Exiftool tag names for lens metadata."""

    LENS_MAKE = "LensMake"
    LENS_MODEL = "LensModel"
    FOCAL_LENGTH = "FocalLength"
    F_NUMBER = "FNumber"
    FOCAL_LENGTH_35MM = "FocalLengthIn35mmFormat"
    LENS_INFO = "LensInfo"
    MAX_APERTURE = "MaxApertureValue"


def _short_error(e: Exception) -> str:
    lines = [ln.strip() for ln in str(e).splitlines() if ln.strip()]
    return lines[-1] if lines else type(e).__name__


@dataclass
class Lens:
    lens_make: Optional[str] = field(default=None, metadata={"exiftool": ExiftoolTag.LENS_MAKE})
    lens_model: Optional[str] = field(default=None, metadata={"exiftool": ExiftoolTag.LENS_MODEL})
    focal_length: Optional[str] = field(default=None, metadata={"exiftool": ExiftoolTag.FOCAL_LENGTH})
    f_number: Optional[str] = field(default=None, metadata={"exiftool": ExiftoolTag.F_NUMBER})
    focal_length_in_35mm_film: Optional[str] = field(default=None, metadata={"exiftool": ExiftoolTag.FOCAL_LENGTH_35MM})
    lens_specification: Optional[Tuple[str, str, str, str]] = field(default=None, metadata={"exiftool": ExiftoolTag.LENS_INFO})
    max_aperture_value: Optional[str] = field(default=None, metadata={"exiftool": ExiftoolTag.MAX_APERTURE})

    def __post_init__(self) -> None:
        """Convert all non-None parameters to string."""
        if self.lens_make is not None:
            self.lens_make = str(self.lens_make)
        if self.lens_model is not None:
            self.lens_model = str(self.lens_model)
        if self.focal_length is not None:
            self.focal_length = str(self.focal_length)
        if self.f_number is not None:
            self.f_number = str(self.f_number)
        if self.focal_length_in_35mm_film is not None:
            self.focal_length_in_35mm_film = str(self.focal_length_in_35mm_film)
        if self.lens_specification is not None:
            self.lens_specification = tuple(str(v) for v in self.lens_specification)
        if self.max_aperture_value is not None:
            self.max_aperture_value = self.max_aperture_value

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_exiftool_dict(self) -> dict:
        result = {}
        if self.lens_make is not None:
            result[ExiftoolTag.LENS_MAKE.value] = self.lens_make
        if self.lens_model is not None:
            result[ExiftoolTag.LENS_MODEL.value] = self.lens_model
        if self.focal_length is not None:
            result[ExiftoolTag.FOCAL_LENGTH.value] = self.focal_length
        if self.f_number is not None:
            result[ExiftoolTag.F_NUMBER.value] = self.f_number
        if self.focal_length_in_35mm_film is not None:
            result[ExiftoolTag.FOCAL_LENGTH_35MM.value] = self.focal_length_in_35mm_film
        if self.lens_specification is not None:
            result[ExiftoolTag.LENS_INFO.value] = " ".join(str(v) for v in self.lens_specification)
        if self.max_aperture_value is not None:
            result[ExiftoolTag.MAX_APERTURE.value] = self.max_aperture_value
        return result


SMC_TAKUMAR_50_1_4 = Lens(
    lens_make="Asahi Opt. Co.",
    lens_model="SMC Takumar 50mm f/1.4",
    focal_length="50",
    f_number="1.4",
    focal_length_in_35mm_film="50",
    lens_specification=("50", "50", "1.4", "1.4"),
    max_aperture_value="1.4",
)

HELIOS_44M = Lens(
    lens_make="KMZ",
    lens_model="Helios-44M 58mm f/2",
    focal_length="58",
    f_number="2.0",
    focal_length_in_35mm_film="58",
    lens_specification=("58", "58", "2", "2"),
    max_aperture_value="2.0",
)

# A Tair sorozatból a 11-es 135/2.8 — ha a "21m" mást jelölne, írd át a megfelelő értékre.
TAIR_11 = Lens(
    lens_make="KMZ",
    lens_model="Tair-11 135mm f/2.8",
    focal_length="135",
    f_number="2.8",
    focal_length_in_35mm_film="135",
    lens_specification=("135", "135", "2.8", "2.8"),
    max_aperture_value="2.8",
)

# A Photosniper (FS-12) készlet objektívje: Tair-3-PhS 300mm f/4.5.
PHOTOSNIPER_TAIR_3 = Lens(
    lens_make="KMZ",
    lens_model="Tair-3-PhS 300mm f/4.5 (Photosniper)",
    focal_length="300",
    f_number="4.5",
    focal_length_in_35mm_film="300",
    lens_specification=("300", "300", "4.5", "4.5"),
    max_aperture_value="4.5",
)

JUPITER_21M = Lens(
    lens_make="MMZ",
    lens_model="Jupiter-21M 200mm f/4",
    focal_length="200",
    f_number="4.0",
    focal_length_in_35mm_film="200",
    lens_specification=("200", "200", "4", "4"),
    max_aperture_value="4.0",
)

JUPITER_37A = Lens(
    lens_make="KMZ",
    lens_model="Jupiter-37A 135mm f/3.5",
    focal_length="135",
    f_number="3.5",
    focal_length_in_35mm_film="135",
    lens_specification=("135", "135", "3.5", "3.5"),
    max_aperture_value="3.5",
)

LENSES = {
    "smc_takumar_50_1_4": SMC_TAKUMAR_50_1_4,
    "helios_44m": HELIOS_44M,
    "tair_11": TAIR_11,
    "photosniper": PHOTOSNIPER_TAIR_3,
    "jupiter_21m": JUPITER_21M,
    "jupiter_37a": JUPITER_37A,
}


class MyExif:
    def __init__(self, lens: Union[Lens, dict], move_up: bool = True, overwrite: bool = False):
        if isinstance(lens, Lens):
            self.lens = lens
        else:
            allowed = {f.name for f in fields(Lens)}
            unknown = set(lens) - allowed
            if unknown:
                print(f"[EXIF] ignoring unknown lens keys: {sorted(unknown)}")
            self.lens = Lens(**{k: v for k, v in lens.items() if k in allowed})
        self.move_up = move_up
        self.overwrite = overwrite
        self._exiftool_helper = None

    def apply_to_path(self, path: str) -> list[str]:
        with self._ensure_session():
            p = Path(path)
            if p.is_dir():
                return self._apply_to_folder(p)
            moved = self._apply_to_file(p)
            return [moved] if moved else []

    @classmethod
    def apply_by_subfolder_names(cls, parent_folder: str, move_up: bool = True, overwrite: bool = False) -> dict[str, list[str]]:
        import exiftool

        parent = Path(parent_folder)
        results: dict[str, list[str]] = {}
        keys_by_length = sorted(LENSES.keys(), key=len, reverse=True)
        with exiftool.ExifToolHelper() as exiftool_helper:
            for child in sorted(parent.iterdir()):
                if not child.is_dir():
                    continue
                name_lower = child.name.lower()
                matched_key = next((k for k in keys_by_length if k in name_lower), None)
                if not matched_key:
                    print(f"[EXIF] no lens match in subfolder name: {child.name} (accepted keys: {', '.join(sorted(LENSES.keys()))})")
                    continue
                lens = LENSES[matched_key]
                print(f"[EXIF] {child.name} -> {matched_key} ({lens.lens_model})")
                instance = cls(lens, move_up=move_up, overwrite=overwrite)
                instance._exiftool_helper = exiftool_helper
                results[child.name] = instance.apply_to_path(str(child))
        return results

    @contextmanager
    def _ensure_session(self):
        if self._exiftool_helper is not None:
            yield
            return
        try:
            import exiftool
        except ImportError:
            print("[EXIF] pyexiftool not installed (pip install pyexiftool)")
            yield
            return
        with exiftool.ExifToolHelper() as exiftool_helper:
            self._exiftool_helper = exiftool_helper
            try:
                yield
            finally:
                self._exiftool_helper = None

    def _apply_to_folder(self, folder: Path) -> list[str]:
        results: list[str] = []
        for root, _, files in os.walk(folder):
            for name in files:
                if name.endswith(IMAGE_EXTENSIONS):
                    moved = self._apply_to_file(Path(root) / name)
                    if moved:
                        results.append(moved)
        return results

    def _apply_to_file(self, path: Path) -> Optional[str]:
        ok = self._write_with_exiftool(path)

        if not ok:
            return None

        # Move file if needed
        final_path = path
        if self.move_up:
            try:
                final_path = Path(self._move_up(path))
            except Exception as e:
                print(f"[EXIF] EXIF written but move failed for {path}: {type(e).__name__}: {_short_error(e)}")
                return None

        # Verify written tags
        if not self._verify_written_tags(final_path):
            return None

        return str(final_path)

    def _write_with_exif_lib(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                img = Image(f)

            # Try to read existing tags - if this fails, EXIF is likely corrupted
            try:
                for tag, value in self.lens.to_dict().items():
                    existing = img.get(tag)
                    if existing is not None and not self.overwrite:
                        print(f"[EXIF] skip {tag} on {path.name}: already set to {existing}")
                        continue
                    img.set(tag, value)
            except Exception as read_error:
                # EXIF is corrupted, fallback to exiftool
                raise read_error

            with open(path, "wb") as f:
                f.write(img.get_file())
            return True
        except Exception as e:
            # If exif lib fails (e.g., corrupted EXIF after deletion), fallback to exiftool
            if self._exiftool_helper is not None:
                print(f"[EXIF] exif lib failed for {path}: {_short_error(e)}, using exiftool...")
                return self._write_with_exiftool(path)
            print(f"[EXIF] write failed for {path}: {type(e).__name__}: {_short_error(e)}")
            return False

    def _write_with_exiftool(self, path: Path) -> bool:
        if self._exiftool_helper is None:
            print(f"[EXIF] no exiftool session for {path} (pyexiftool not installed?)")
            return False
        try:
            # Read existing tags to avoid overwriting already set values (if not overwrite mode)
            existing_data = self._exiftool_helper.execute_json(str(path))
            existing_tags = existing_data[0] if existing_data else {}

            # Build tag arguments for exiftool
            tag_args = []
            for tag, value in self.lens.to_exiftool_dict().items():
                # exiftool returns tags with EXIF: prefix in execute_json output
                existing_tag_key = f"EXIF:{tag}"
                if existing_tag_key not in existing_tags or not existing_tags[existing_tag_key]:
                    tag_args.append(f"-{tag}={value}")
                elif self.overwrite:
                    tag_args.append(f"-{tag}={value}")
                else:
                    print(f"[EXIF] skip {tag} on {path.name}: already set to {existing_tags[existing_tag_key]}")

            # Write tags if there are any to write
            if tag_args:
                self._exiftool_helper.execute(*tag_args, "-overwrite_original", str(path))
            return True
        except Exception as e:
            print(f"[EXIF] exiftool failed for {path}: {type(e).__name__}: {_short_error(e)}")
            return False

    def _verify_written_tags(self, path: Path) -> bool:
        """Verify that lens tags were written correctly to file.

        Compares expected (from self.lens) vs actual (read from file) values.
        Logs errors if mismatch found.
        Uses fresh exiftool session to avoid caching issues from write session.
        Tolerates float precision differences for numeric EXIF tags.
        """
        actual = self.read_lens_tags(str(path), exiftool_helper=None)
        expected = self.lens.to_exiftool_dict()

        # Map exiftool tag names to enum names for lookup in actual dict
        exif_to_enum = {tag.value: tag.name for tag in ExiftoolTag}

        # Tags that may be stored as rational numbers with float precision issues
        FLOAT_TAGS = {
            ExiftoolTag.MAX_APERTURE.value,  # MaxApertureValue — APEX rational
            ExiftoolTag.F_NUMBER.value,  # FNumber — rational
            ExiftoolTag.FOCAL_LENGTH.value,  # FocalLength — rational
        }

        errors = []
        for exif_tag_name, expected_value in expected.items():
            enum_name = exif_to_enum.get(exif_tag_name)
            actual_value = actual.get(enum_name)

            # Use float tolerance for numeric tags, string comparison for others
            if exif_tag_name in FLOAT_TAGS:
                try:
                    if expected_value != str(round(actual_value, 2)):
                        errors.append(f"{exif_tag_name}: expected {expected_value}, got {actual_value}")
                except (TypeError, ValueError):
                    errors.append(f"{exif_tag_name}: expected {expected_value}, got {actual_value} (not numeric)")
            else:
                if str(actual_value) != str(expected_value):
                    errors.append(f"{exif_tag_name}: expected {expected_value}, got {actual_value}")

        if errors:
            print(f"[EXIF] Verification failed for {path.name}:")
            for error in errors:
                print(f"  - {error}")
            return False

        return True

    @staticmethod
    def delete_lens_tags(file_path: str) -> bool:
        """Delete all lens-related EXIF tags from a file.

        Removes all tags defined in ExiftoolTag enum (lens metadata).
        """
        try:
            import exiftool

            with exiftool.ExifToolHelper() as exiftool_helper:
                # Build list of tags to delete with exiftool syntax (use = to actually clear them)
                tags_to_delete = [f"-{tag.value}=" for tag in ExiftoolTag]
                exiftool_helper.execute(*tags_to_delete, "-overwrite_original", str(file_path))
            return True
        except ImportError:
            print("[EXIF] pyexiftool not installed (pip install pyexiftool)")
            return False
        except Exception as e:
            print(f"[EXIF] failed to delete tags from {file_path}: {type(e).__name__}: {_short_error(e)}")
            return False

    @staticmethod
    def get_exif_datetime(file_path: str) -> Optional[datetime]:
        """Extract photo datetime from EXIF (JPEG, raw, video).

        Returns datetime_original if available (when photo was taken),
        falls back to other datetime tags.
        """
        path = Path(file_path)
        # Try with exiftool for raw/video/others
        try:
            import exiftool

            with exiftool.ExifToolHelper() as exiftool_helper:
                tags_list = exiftool_helper.execute_json(str(path))
                if not tags_list:
                    return None
                tag_dict = tags_list[0]
                # Try common datetime tags (exiftool returns with EXIF: prefix)
                dt_str = (
                    tag_dict.get("EXIF:DateTimeOriginal")
                    or tag_dict.get("EXIF:CreateDate")
                    or tag_dict.get("EXIF:ModifyDate")
                    or tag_dict.get("EXIF:CreationTime")
                )
                if dt_str:
                    # Handle different datetime formats
                    for fmt in ["%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
                        try:
                            return datetime.strptime(dt_str.split("+")[0].strip(), fmt)
                        except ValueError:
                            continue
        except ImportError:
            pass
        except Exception:
            pass

        return None

    @staticmethod
    def read_lens_tags(file_path: str, exiftool_helper: Optional[object] = None) -> dict[str, Optional[str]]:
        """Read all lens-related EXIF tags from a file.

        Returns a dictionary mapping tag names to their values.
        If exiftool_helper is provided, uses it for raw/video files (for freshly written data).
        """
        path = Path(file_path)
        result = {tag.name: None for tag in ExiftoolTag}
        try:
            import exiftool

            # Setup helper: use provided or create new
            if exiftool_helper is None:
                exiftool_helper = exiftool.ExifToolHelper()
                exiftool_helper.__enter__()
                should_close = True
            else:
                should_close = False

            try:
                tags_list = exiftool_helper.execute_json(str(path))
                if tags_list:
                    tag_dict = tags_list[0]
                    for tag in ExiftoolTag:
                        # exiftool returns tags with EXIF: prefix
                        value = tag_dict.get(f"EXIF:{tag.value}")
                        if value is not None:
                            result[tag.name] = value
            finally:
                if should_close:
                    exiftool_helper.__exit__(None, None, None)
        except ImportError:
            pass
        except Exception:
            pass

        return result

    @staticmethod
    def print_lens_tags_table(folder_path: str) -> None:
        """Print lens metadata for all images in a folder in table format."""
        path = Path(folder_path)

        if not path.exists():
            print(f"Error: Folder '{folder_path}' does not exist")
            return

        if not path.is_dir():
            print(f"Error: '{folder_path}' is not a directory")
            return

        # Collect image files (including subdirectories)
        image_files = []
        for root, _, files in os.walk(path):
            for name in files:
                if name.endswith(IMAGE_EXTENSIONS):
                    image_files.append(Path(root) / name)

        if not image_files:
            print(f"No image files found in '{folder_path}'")
            return

        # Use a single exiftool session for all reads (important for ARW files)
        try:
            import exiftool

            with exiftool.ExifToolHelper() as exiftool_helper:
                table_data = []
                for file_path in sorted(image_files):
                    tags = MyExif.read_lens_tags(str(file_path), exiftool_helper)
                    table_data.append((file_path.name, tags))
        except ImportError:
            # Fallback without exiftool
            table_data = []
            for file_path in sorted(image_files):
                tags = MyExif.read_lens_tags(str(file_path))
                table_data.append((file_path.name, tags))

        # Print header
        tag_names = [tag.name for tag in ExiftoolTag]
        header_parts = ["Fájl"] + tag_names

        # Calculate column widths
        col_widths = [max(len(header_parts[0]), max((len(row[0]) for row in table_data), default=0))]
        for tag_name in tag_names:
            max_width = len(tag_name)
            for _, tags in table_data:
                value = tags.get(tag_name)
                if value:
                    max_width = max(max_width, len(str(value)))
            col_widths.append(max_width)

        # Print header
        header = " | ".join(header_parts[i].ljust(col_widths[i]) for i in range(len(header_parts)))
        print(header)
        print("-" * len(header))

        # Print rows
        for file_name, tags in table_data:
            row_parts = [file_name] + [str(tags.get(tag_name)) or "-" for tag_name in tag_names]
            row = " | ".join(row_parts[i].ljust(col_widths[i]) for i in range(len(row_parts)))
            print(row)

        print(f"\nÖsszesen: {len(table_data)} fájl")

    @staticmethod
    def _move_up(path: Path) -> str:
        dest = path.parent.parent / path.name
        if dest.exists():
            raise FileExistsError(f"destination already exists: {dest}")
        shutil.move(str(path), str(dest))
        return str(dest)
