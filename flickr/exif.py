import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field, fields
from pathlib import Path
from typing import Optional, Tuple, Union

from exif import Image


JPEG_EXTENSIONS = (".jpg", ".jpeg", ".JPG", ".JPEG")
EXIFTOOL_EXTENSIONS = (".ARW", ".CR2", ".NEF", ".DNG", ".TIFF", ".PNG", ".GIF", ".BMP")
IMAGE_EXTENSIONS = JPEG_EXTENSIONS + EXIFTOOL_EXTENSIONS


def _short_error(e: Exception) -> str:
    lines = [ln.strip() for ln in str(e).splitlines() if ln.strip()]
    return lines[-1] if lines else type(e).__name__


@dataclass
class Lens:
    lens_make: Optional[str] = field(default=None, metadata={"exiftool": "LensMake"})
    lens_model: Optional[str] = field(default=None, metadata={"exiftool": "LensModel"})
    focal_length: Optional[float] = field(default=None, metadata={"exiftool": "FocalLength"})
    f_number: Optional[float] = field(default=None, metadata={"exiftool": "FNumber"})
    focal_length_in_35mm_film: Optional[int] = field(default=None, metadata={"exiftool": "FocalLengthIn35mmFormat"})
    lens_specification: Optional[Tuple[float, float, float, float]] = field(default=None, metadata={"exiftool": "LensInfo"})
    max_aperture_value: Optional[float] = field(default=None, metadata={"exiftool": "MaxApertureValue"})

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_exiftool_dict(self) -> dict:
        result = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if value is None:
                continue
            tag = f.metadata.get("exiftool")
            if not tag:
                continue
            if isinstance(value, (tuple, list)):
                value = " ".join(str(v) for v in value)
            result[tag] = value
        return result


SMC_TAKUMAR_50_1_4 = Lens(
    lens_make="Asahi Opt. Co.",
    lens_model="SMC Takumar 50mm f/1.4",
    focal_length=50.0,
    f_number=1.4,
    focal_length_in_35mm_film=50,
    lens_specification=(50.0, 50.0, 1.4, 1.4),
    max_aperture_value=1.4,
)

HELIOS_44M = Lens(
    lens_make="KMZ",
    lens_model="Helios-44M 58mm f/2",
    focal_length=58.0,
    f_number=2.0,
    focal_length_in_35mm_film=58,
    lens_specification=(58.0, 58.0, 2.0, 2.0),
    max_aperture_value=2.0,
)

# A Tair sorozatból a 11-es 135/2.8 — ha a "21m" mást jelölne, írd át a megfelelő értékre.
TAIR_11 = Lens(
    lens_make="KMZ",
    lens_model="Tair-11 135mm f/2.8",
    focal_length=135.0,
    f_number=2.8,
    focal_length_in_35mm_film=135,
    lens_specification=(135.0, 135.0, 2.8, 2.8),
    max_aperture_value=2.8,
)

# A Photosniper (FS-12) készlet objektívje: Tair-3-PhS 300mm f/4.5.
PHOTOSNIPER_TAIR_3 = Lens(
    lens_make="KMZ",
    lens_model="Tair-3-PhS 300mm f/4.5 (Photosniper)",
    focal_length=300.0,
    f_number=4.5,
    focal_length_in_35mm_film=300,
    lens_specification=(300.0, 300.0, 4.5, 4.5),
    max_aperture_value=4.5,
)

JUPITER_21M = Lens(
    lens_make="MMZ",
    lens_model="Jupiter-21M 200mm f/4",
    focal_length=200.0,
    f_number=4.0,
    focal_length_in_35mm_film=200,
    lens_specification=(200.0, 200.0, 4.0, 4.0),
    max_aperture_value=4.0,
)

JUPITER_37A = Lens(
    lens_make="KMZ",
    lens_model="Jupiter-37A 135mm f/3.5",
    focal_length=135.0,
    f_number=3.5,
    focal_length_in_35mm_film=135,
    lens_specification=(135.0, 135.0, 3.5, 3.5),
    max_aperture_value=3.5,
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
    def __init__(self, lens: Union[Lens, dict]):
        if isinstance(lens, Lens):
            self.lens = lens
        else:
            allowed = {f.name for f in fields(Lens)}
            unknown = set(lens) - allowed
            if unknown:
                print(f"[EXIF] ignoring unknown lens keys: {sorted(unknown)}")
            self.lens = Lens(**{k: v for k, v in lens.items() if k in allowed})
        self._et = None

    def apply_to_path(self, path: str) -> list[str]:
        with self._ensure_session():
            p = Path(path)
            if p.is_dir():
                return self._apply_to_folder(p)
            moved = self._apply_to_file(p)
            return [moved] if moved else []

    @classmethod
    def apply_by_subfolder_names(cls, parent_folder: str) -> dict[str, list[str]]:
        import exiftool

        parent = Path(parent_folder)
        results: dict[str, list[str]] = {}
        keys_by_length = sorted(LENSES.keys(), key=len, reverse=True)
        with exiftool.ExifToolHelper() as et:
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
                instance = cls(lens)
                instance._et = et
                results[child.name] = instance.apply_to_path(str(child))
        return results

    @contextmanager
    def _ensure_session(self):
        if self._et is not None:
            yield
            return
        try:
            import exiftool
        except ImportError:
            print("[EXIF] pyexiftool not installed (pip install pyexiftool)")
            yield
            return
        with exiftool.ExifToolHelper() as et:
            self._et = et
            try:
                yield
            finally:
                self._et = None

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
        if path.suffix in JPEG_EXTENSIONS:
            ok = self._write_with_exif_lib(path)
        elif path.suffix in EXIFTOOL_EXTENSIONS:
            ok = self._write_with_exiftool(path)
        else:
            print(f"[EXIF] unsupported extension: {path}")
            return None

        if not ok:
            return None

        try:
            return self._move_up(path)
        except Exception as e:
            print(f"[EXIF] EXIF written but move failed for {path}: {type(e).__name__}: {_short_error(e)}")
            return None

    def _write_with_exif_lib(self, path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                img = Image(f)
            for tag, value in self.lens.to_dict().items():
                try:
                    img.set(tag, value)
                except Exception as e:
                    print(f"[EXIF] skip {tag} on {path.name}: {e}")
            with open(path, "wb") as f:
                f.write(img.get_file())
            return True
        except Exception as e:
            print(f"[EXIF] write failed for {path}: {type(e).__name__}: {_short_error(e)}")
            return False

    def _write_with_exiftool(self, path: Path) -> bool:
        if self._et is None:
            print(f"[EXIF] no exiftool session for {path} (pyexiftool not installed?)")
            return False
        try:
            self._et.set_tags([str(path)], tags=self.lens.to_exiftool_dict(), params=["-overwrite_original"])
            return True
        except Exception as e:
            print(f"[EXIF] exiftool failed for {path}: {type(e).__name__}: {_short_error(e)}")
            return False

    @staticmethod
    def _move_up(path: Path) -> str:
        dest = path.parent.parent / path.name
        if dest.exists():
            raise FileExistsError(f"destination already exists: {dest}")
        shutil.move(str(path), str(dest))
        return str(dest)
