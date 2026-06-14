import os
import queue
import threading
import tkinter as tk
import traceback
from contextlib import redirect_stderr, redirect_stdout
from tkinter import filedialog, ttk

from flickr.exif import LENSES, MyExif
from flickr.organize import organize_files_by_date
from flickr.upload_folder import sync_folder, upload_multiple_folders, upload_single_folder


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

        self._build_layout()
        self._show_form(self._build_upload_form, "Feltöltés")
        self.root.after(100, self._drain_output)

    # ---------- layout ----------
    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=8)
        outer.pack(fill="both", expand=True)

        top = ttk.Frame(outer)
        top.pack(fill="both", expand=True)

        sidebar = ttk.Frame(top, padding=(0, 0, 8, 0))
        sidebar.pack(side="left", fill="y")

        self._make_sidebar_button(sidebar, "Feltöltés", self._build_upload_form)
        self._make_sidebar_button(sidebar, "Objektív EXIF", self._build_exif_form)
        self._make_sidebar_button(sidebar, "Rendezés dátum szerint", self._build_organize_form)

        self.form_container = ttk.LabelFrame(top, text="Paraméterek", padding=12)
        self.form_container.pack(side="left", fill="both", expand=True)

        bottom = ttk.LabelFrame(outer, text="Kimenet", padding=4)
        bottom.pack(fill="both", expand=True, pady=(8, 0))

        self.output = tk.Text(bottom, wrap="word", height=14, bg="#1e1e1e", fg="#dcdcdc", insertbackground="#dcdcdc")
        self.output.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(bottom, command=self.output.yview)
        scroll.pack(side="right", fill="y")
        self.output.configure(yscrollcommand=scroll.set)

    def _make_sidebar_button(self, parent: ttk.Frame, label: str, builder) -> None:
        btn = ttk.Button(parent, text=label, width=24, command=lambda: self._show_form(builder, label))
        btn.pack(pady=4, anchor="n")

    def _show_form(self, builder, label: str) -> None:
        self.form_container.config(text=label)
        for w in self.form_container.winfo_children():
            w.destroy()
        builder(self.form_container)

    # ---------- form helpers ----------
    @staticmethod
    def _row(parent, label_text: str, row: int) -> None:
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)

    def _single_folder_picker(self, parent, row: int) -> tk.StringVar:
        var = tk.StringVar()
        ttk.Entry(parent, textvariable=var, width=60).grid(row=row, column=1, sticky="we", pady=4)
        ttk.Button(parent, text="Tallózás…", command=lambda: self._pick_folder(var)).grid(row=row, column=2, padx=(8, 0), pady=4)
        parent.columnconfigure(1, weight=1)
        return var

    @staticmethod
    def _pick_folder(var: tk.StringVar) -> None:
        path = filedialog.askdirectory(initialdir=var.get() or os.path.expanduser("~"))
        if path:
            var.set(path)

    # ---------- forms ----------
    def _build_upload_form(self, parent: ttk.Frame) -> None:
        self._row(parent, "Mód:", 0)
        mode = tk.StringVar(value="folder")
        ttk.Combobox(parent, textvariable=mode, state="readonly",
                     values=["folder", "folders", "sync_folder"], width=30).grid(row=0, column=1, sticky="w", pady=4)

        folder_area = ttk.Frame(parent)
        folder_area.grid(row=1, column=0, columnspan=3, sticky="we", pady=4)
        parent.columnconfigure(1, weight=1)

        state: dict = {}

        def rebuild_folder_area(*_) -> None:
            for w in folder_area.winfo_children():
                w.destroy()
            if mode.get() == "folders":
                ttk.Label(folder_area, text="Mappák:").grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=4)
                listbox = tk.Listbox(folder_area, height=6, selectmode="extended")
                listbox.grid(row=0, column=1, sticky="we", pady=4)
                folder_area.columnconfigure(1, weight=1)
                btns = ttk.Frame(folder_area)
                btns.grid(row=0, column=2, sticky="n", padx=(8, 0))

                def _add() -> None:
                    p = filedialog.askdirectory()
                    if p:
                        listbox.insert("end", p)

                def _remove() -> None:
                    for i in reversed(listbox.curselection()):
                        listbox.delete(i)

                ttk.Button(btns, text="Hozzáadás…", command=_add).pack(fill="x")
                ttk.Button(btns, text="Eltávolítás", command=_remove).pack(fill="x", pady=(4, 0))
                state["kind"] = "multi"
                state["listbox"] = listbox
            else:
                ttk.Label(folder_area, text="Mappa:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
                var = tk.StringVar()
                ttk.Entry(folder_area, textvariable=var).grid(row=0, column=1, sticky="we", pady=4)
                folder_area.columnconfigure(1, weight=1)
                ttk.Button(folder_area, text="Tallózás…", command=lambda: self._pick_folder(var)).grid(row=0, column=2, padx=(8, 0))
                state["kind"] = "single"
                state["var"] = var

        mode.trace_add("write", rebuild_folder_area)
        rebuild_folder_area()

        self._row(parent, "API key:", 2)
        api_key = tk.StringVar(value=os.environ.get("FLICKR_API_KEY", ""))
        ttk.Entry(parent, textvariable=api_key, width=60).grid(row=2, column=1, sticky="we", pady=4)

        self._row(parent, "API secret:", 3)
        api_secret = tk.StringVar(value=os.environ.get("FLICKR_API_SECRET", ""))
        ttk.Entry(parent, textvariable=api_secret, width=60, show="•").grid(row=3, column=1, sticky="we", pady=4)

        upload_failed = tk.IntVar(value=0)
        ttk.Checkbutton(parent, text="FAILED mappa újrapróbálása", variable=upload_failed).grid(row=4, column=1, sticky="w", pady=4)

        def run() -> None:
            ak = api_key.get().strip()
            asec = api_secret.get().strip()
            uf = bool(upload_failed.get())
            if state["kind"] == "multi":
                lb = state["listbox"]
                paths = [lb.get(i).strip() for i in range(lb.size()) if lb.get(i).strip()]
                if not paths:
                    self._append("Hiba: adj meg legalább egy mappát.\n")
                    return
                self._run_in_background("Feltöltés (folders)", upload_multiple_folders, paths, ak, asec, uf)
            else:
                folder_value = state["var"].get().strip()
                if not folder_value:
                    self._append("Hiba: válassz mappát.\n")
                    return
                if mode.get() == "folder":
                    self._run_in_background("Feltöltés (folder)", upload_single_folder, folder_value, ak, asec, uf)
                else:
                    self._run_in_background("Feltöltés (sync)", sync_folder, folder_value, ak, asec, uf)

        ttk.Button(parent, text="Futtatás", command=run).grid(row=5, column=1, sticky="e", pady=(16, 0))

    def _build_exif_form(self, parent: ttk.Frame) -> None:
        self._row(parent, "Mappa:", 0)
        folder = self._single_folder_picker(parent, 0)

        self._row(parent, "Objektív:", 1)
        lens = tk.StringVar(value="auto")
        values = ["auto"] + sorted(LENSES.keys())
        ttk.Combobox(parent, textvariable=lens, state="readonly", values=values, width=30).grid(row=1, column=1, sticky="w", pady=4)

        def run() -> None:
            folder_value = folder.get().strip()
            if not folder_value:
                self._append("Hiba: válassz mappát.\n")
                return
            lens_key = lens.get()
            if lens_key == "auto":
                self._run_in_background("EXIF (auto)", _run_auto_exif, folder_value)
            else:
                self._run_in_background(f"EXIF ({lens_key})", _run_single_lens_exif, folder_value, lens_key)

        ttk.Button(parent, text="Futtatás", command=run).grid(row=2, column=1, sticky="e", pady=(16, 0))

    def _build_organize_form(self, parent: ttk.Frame) -> None:
        self._row(parent, "Mappa:", 0)
        folder = self._single_folder_picker(parent, 0)

        def run() -> None:
            folder_value = folder.get().strip()
            if not folder_value:
                self._append("Hiba: válassz mappát.\n")
                return
            self._run_in_background("Rendezés dátum szerint", organize_files_by_date, folder_value)

        ttk.Button(parent, text="Futtatás", command=run).grid(row=1, column=1, sticky="e", pady=(16, 0))

    # ---------- background runner ----------
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


def _run_auto_exif(folder: str) -> None:
    results = MyExif.apply_by_subfolder_names(folder)
    total = sum(len(v) for v in results.values())
    print(f"Done. {total} file(s) modified across {len(results)} subfolder(s).")


def _run_single_lens_exif(folder: str, lens_key: str) -> None:
    lens = LENSES[lens_key]
    print(f"Applying '{lens.lens_model}' to folder: {folder}")
    moved = MyExif(lens).apply_to_path(folder)
    print(f"Done. {len(moved)} file(s) modified and moved one level up.")


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
