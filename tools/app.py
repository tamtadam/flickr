import os
import queue
import threading
import tkinter as tk
import traceback
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tkinter import filedialog, ttk

from flickr.exif import LENSES, MyExif
from flickr.organize import organize_files_by_date
from flickr.upload_folder import UPLOAD_ROOT, sync_folder, upload_multiple_folders, upload_single_folder


class QueueWriter:
    def __init__(self, q: queue.Queue) -> None:
        self.q = q

    def write(self, s: str) -> int:
        if s:
            self.q.put(s)
        return len(s)

    def flush(self) -> None:
        pass


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Flickr Tools")
        self.root.geometry("980x640")

        self.output_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.action_params: dict = {}

        self.upload_root = tk.StringVar(value=os.environ.get("UPLOAD_ROOT", UPLOAD_ROOT or os.path.expanduser("~")))

        self._build_layout()
        self.root.after(100, self._drain_output)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill="both", expand=True)

        top = ttk.LabelFrame(outer, text="Paraméterek", padding=12)
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Mappák:").grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=4)
        self.listbox = tk.Listbox(top, height=5, selectmode="extended")
        self.listbox.grid(row=0, column=1, sticky="we", pady=4)

        btns = ttk.Frame(top)
        btns.grid(row=0, column=2, sticky="n", padx=(8, 0))
        ttk.Button(btns, text="Hozzáadás…", command=self._add_folder).pack(fill="x")
        ttk.Button(btns, text="Eltávolítás", command=self._remove_folder).pack(fill="x", pady=(4, 0))

        ttk.Label(top, text="Akció:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.action = tk.StringVar(value="Feltöltés")
        ttk.Combobox(
            top, textvariable=self.action, state="readonly",
            values=["Feltöltés", "Szinkronizálás", "Objektív EXIF", "Rendezés dátum szerint"], width=30,
        ).grid(row=1, column=1, sticky="w", pady=4)
        self.action.trace_add("write", self._rebuild_params)

        self.params_frame = ttk.Frame(top)
        self.params_frame.grid(row=2, column=0, columnspan=3, sticky="we")
        self.params_frame.columnconfigure(1, weight=1)
        self._rebuild_params()

        ttk.Button(top, text="Futtatás", command=self._run).grid(row=3, column=1, sticky="e", pady=(8, 0))

        bottom = ttk.LabelFrame(outer, text="Kimenet", padding=4)
        bottom.pack(fill="both", expand=True, pady=(8, 0))
        self.output = tk.Text(bottom, wrap="word", height=14, bg="#1e1e1e", fg="#dcdcdc", insertbackground="#dcdcdc")
        self.output.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(bottom, command=self.output.yview)
        scroll.pack(side="right", fill="y")
        self.output.configure(yscrollcommand=scroll.set)

    def _add_folder(self) -> None:
        p = filedialog.askdirectory(initialdir=self.upload_root.get() or os.path.expanduser("~"))
        if p:
            self.listbox.insert("end", p)

    def _remove_folder(self) -> None:
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)

    def _rebuild_params(self, *_: object) -> None:
        for w in self.params_frame.winfo_children():
            w.destroy()
        self.action_params = {}
        act = self.action.get()
        if act in ("Feltöltés", "Szinkronizálás"):
            self._build_upload_params(self.params_frame)
        elif act == "Objektív EXIF":
            self._build_exif_params(self.params_frame)
        elif act == "Rendezés dátum szerint":
            self._build_organize_params(self.params_frame)

    def _build_upload_params(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Alapmappa:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(parent, textvariable=self.upload_root, width=60).grid(row=0, column=1, sticky="we", pady=4)
        ttk.Button(parent, text="Tallózás…", command=lambda: self._pick_folder(self.upload_root)).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(parent, text="API key:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        api_key = tk.StringVar(value=os.environ.get("FLICKR_API_KEY", ""))
        ttk.Entry(parent, textvariable=api_key, width=60).grid(row=1, column=1, sticky="we", pady=4)

        ttk.Label(parent, text="API secret:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        api_secret = tk.StringVar(value=os.environ.get("FLICKR_API_SECRET", ""))
        ttk.Entry(parent, textvariable=api_secret, width=60, show="•").grid(row=2, column=1, sticky="we", pady=4)

        ttk.Label(parent, text="Év set:").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=4)
        year_set = tk.StringVar(value="__2026__")
        ttk.Entry(parent, textvariable=year_set, width=20).grid(row=3, column=1, sticky="w", pady=4)

        upload_failed = tk.IntVar(value=0)
        ttk.Checkbutton(parent, text="FAILED mappa újrapróbálása", variable=upload_failed).grid(row=4, column=1, sticky="w", pady=4)

        self.action_params = {"api_key": api_key, "api_secret": api_secret, "upload_failed": upload_failed, "year_set": year_set}

    def _build_exif_params(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Objektív:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        lens = tk.StringVar(value="auto")
        ttk.Combobox(parent, textvariable=lens, state="readonly",
                     values=["auto"] + sorted(LENSES.keys()), width=30).grid(row=0, column=1, sticky="w", pady=4)
        move_up = tk.IntVar(value=1)
        ttk.Checkbutton(parent, text="Fájlok mozgatása egy mappával felfelé", variable=move_up).grid(row=1, column=1, sticky="w", pady=4)
        overwrite = tk.IntVar(value=0)
        ttk.Checkbutton(parent, text="EXIF felülírása (ha már létezik)", variable=overwrite).grid(row=2, column=1, sticky="w", pady=4)
        delete_tags = tk.IntVar(value=0)
        ttk.Checkbutton(parent, text="Meglévő objektív tag-ek törlése", variable=delete_tags).grid(row=3, column=1, sticky="w", pady=4)
        write_exif = tk.IntVar(value=1)
        ttk.Checkbutton(parent, text="EXIF írása", variable=write_exif).grid(row=4, column=1, sticky="w", pady=4)
        show_metadata = tk.IntVar(value=0)
        ttk.Checkbutton(parent, text="Metaadatok megjelenítése után", variable=show_metadata).grid(row=5, column=1, sticky="w", pady=4)
        self.action_params = {"lens": lens, "move_up": move_up, "overwrite": overwrite, "delete_tags": delete_tags, "write_exif": write_exif, "show_metadata": show_metadata}

    def _build_organize_params(self, parent: ttk.Frame) -> None:
        pass  # No additional parameters needed for organize

    def _run(self) -> None:
        paths = [self.listbox.get(i).strip() for i in range(self.listbox.size()) if self.listbox.get(i).strip()]
        if not paths:
            self._append("Hiba: adj meg legalább egy mappát.\n")
            return

        act = self.action.get()
        p = self.action_params

        if act == "Feltöltés":
            ak = p["api_key"].get().strip()
            asec = p["api_secret"].get().strip()
            uf = bool(p["upload_failed"].get())
            ur = self.upload_root.get().strip() or "/"
            ys = p["year_set"].get().strip() or "__2026__"
            names = [os.path.basename(path) for path in paths]
            if len(names) == 1:
                self._run_in_background("Feltöltés", upload_single_folder, names[0], ak, asec, uf, ur, ys)
            else:
                self._run_in_background("Feltöltés (több mappa)", upload_multiple_folders, names, ak, asec, uf, ur, ys)

        elif act == "Szinkronizálás":
            ak = p["api_key"].get().strip()
            asec = p["api_secret"].get().strip()
            uf = bool(p["upload_failed"].get())
            ys = p["year_set"].get().strip() or "__2026__"
            if len(paths) > 1:
                self._append("Figyelem: szinkronizáláshoz csak az első mappa kerül feldolgozásra.\n")
            self._run_in_background("Szinkronizálás", sync_folder, paths[0], ak, asec, uf, ys)

        elif act == "Objektív EXIF":
            lens_key = p["lens"].get()
            move_up = bool(p["move_up"].get())
            overwrite = bool(p["overwrite"].get())
            delete_tags = bool(p["delete_tags"].get())
            write_exif = bool(p["write_exif"].get())
            show_metadata = bool(p["show_metadata"].get())
            if len(paths) > 1:
                self._append("Figyelem: EXIF átíráshoz csak az első mappa kerül feldolgozásra.\n")
            if lens_key == "auto":
                self._run_in_background("EXIF (auto)", _run_auto_exif, paths[0], move_up, overwrite, delete_tags, write_exif, show_metadata)
            else:
                self._run_in_background(f"EXIF ({lens_key})", _run_single_lens_exif, paths[0], lens_key, move_up, overwrite, delete_tags, write_exif, show_metadata)

        elif act == "Rendezés dátum szerint":
            if len(paths) > 1:
                self._append("Figyelem: rendezéshez csak az első mappa kerül feldolgozásra.\n")
            self._run_in_background("Rendezés dátum szerint", organize_files_by_date, paths[0])

    @staticmethod
    def _pick_folder(var: tk.StringVar) -> None:
        path = filedialog.askdirectory(initialdir=var.get() or os.path.expanduser("~"))
        if path:
            var.set(path)

    def _run_in_background(self, label: str, fn, *args, **kwargs) -> None:
        if self.worker and self.worker.is_alive():
            self._append("[FIGYELEM] Egy futás már zajlik, várd meg amíg befejeződik.\n")
            return
        self._append(f"\n=== {label} ===\n")
        writer = QueueWriter(self.output_queue)

        def target() -> None:
            try:
                with redirect_stdout(writer), redirect_stderr(writer):
                    fn(*args, **kwargs)
                self.output_queue.put(f"\n[Kész — {label}]\n")
            except Exception as e:
                self.output_queue.put(f"\n[HIBA] {type(e).__name__}: {e}\n")
                self.output_queue.put(traceback.format_exc())

        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def _drain_output(self) -> None:
        try:
            while True:
                line = self.output_queue.get_nowait()
                self._append(line)
        except queue.Empty:
            pass
        self.root.after(100, self._drain_output)

    def _append(self, text: str) -> None:
        self.output.insert("end", text)
        self.output.see("end")


def _run_auto_exif(folder: str, move_up: bool = True, overwrite: bool = False, delete_tags: bool = False, write_exif: bool = True, show_metadata: bool = False) -> None:
    if delete_tags:
        print("[EXIF] Deleting existing lens tags before applying...")
        _delete_tags_recursively(folder)
    if write_exif:
        results = MyExif.apply_by_subfolder_names(folder, move_up=move_up, overwrite=overwrite)
        total = sum(len(v) for v in results.values())
        action = "modified and moved one level up" if move_up else "modified"
        print(f"Done. {total} file(s) {action} across {len(results)} subfolder(s).")
    else:
        print("[EXIF] EXIF writing disabled, only deletion performed.")

    if show_metadata:
        print("\n=== Metaadatok ===\n")
        MyExif.print_lens_tags_table(folder)


def _run_single_lens_exif(folder: str, lens_key: str, move_up: bool = True, overwrite: bool = False, delete_tags: bool = False, write_exif: bool = True, show_metadata: bool = False) -> None:
    if delete_tags:
        print("[EXIF] Deleting existing lens tags before applying...")
        _delete_tags_recursively(folder)
    if write_exif:
        lens = LENSES[lens_key]
        print(f"Applying '{lens.lens_model}' to folder: {folder}")
        moved = MyExif(lens, move_up=move_up, overwrite=overwrite).apply_to_path(folder)
        action = "modified and moved one level up" if move_up else "modified"
        print(f"Done. {len(moved)} file(s) {action}.")
    else:
        print("[EXIF] EXIF writing disabled, only deletion performed.")

    if show_metadata:
        print("\n=== Metaadatok ===\n")
        MyExif.print_lens_tags_table(folder)


def _delete_tags_recursively(folder: str) -> None:
    """Delete lens tags from all image files in a folder recursively."""
    from flickr.exif import IMAGE_EXTENSIONS

    folder_path = Path(folder)
    deleted_count = 0
    for root, _, files in os.walk(folder_path):
        for name in files:
            if name.endswith(IMAGE_EXTENSIONS):
                file_path = os.path.join(root, name)
                if MyExif.delete_lens_tags(file_path):
                    print(f"[EXIF] Deleted tags from: {name}")
                    deleted_count += 1
    print(f"[EXIF] Successfully deleted lens tags from {deleted_count} file(s).")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
