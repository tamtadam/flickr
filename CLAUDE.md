# Flickr Photo Management Tool

## Development Notes

### Auto-formatting with Ruff

Every Python file edit is automatically checked and fixed with ruff to maintain code quality:
- Import sorting
- Unused import removal
- Style/formatting fixes

The hook is configured at the `/dev` project level in `/dev/.claude/settings.json` and runs via `/dev/.claude/ruff-fixer.py`. It applies to all projects under `/dev`.

### Project Structure

- `flickr/exif.py` — EXIF metadata handling with ThreadPoolExecutor parallelization
- `flickr/organize.py` — File organization by date
- `tools/app.py` — Tkinter GUI for photo management
- `scripts/` — Utility scripts

### Recent Changes

- Added ThreadPoolExecutor to `_apply_to_folder()` for parallel EXIF writing (8 workers)
- Added ThreadPoolExecutor to `print_lens_tags_table()` for parallel tag reading
- Each thread has its own exiftool session (thread-safe)
- Float precision tolerance in `_verify_written_tags()` for numeric EXIF tags
