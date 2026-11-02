"""Small, standard-library-only CSV merger. Python 3.10+."""
import csv
import os
import queue
import sys
import tempfile
import threading
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    tk = None


class Cancelled(Exception):
    pass


def merge_csv(files, output, delimiter=",", encoding="utf-8-sig",
              keep_header=True, cancel=None, notify=lambda text: None):
    """Read each input once; validate and stream into a temporary output.

    Every nonempty input must have one header record. Blank records are skipped.
    Existing output is replaced only after success. Returns data record count.
    """
    cancel = cancel or threading.Event()
    files = [Path(p).resolve() for p in files]
    output = Path(output).resolve()
    if not files:
        raise ValueError("Select at least one file.")
    if output in files:
        raise ValueError("The output cannot be one of the selected input files.")
    header = None
    temp = None
    count = 0
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig",
                newline="", dir=output.parent, prefix=".csv-merge-",
                suffix=".tmp", delete=False) as dest:
            temp = Path(dest.name)
            writer = csv.writer(dest, delimiter=delimiter)
            for index, path in enumerate(files, 1):
                if cancel.is_set():
                    raise Cancelled()
                notify(f"File {index}/{len(files)}: {path.name}")
                with path.open(encoding=encoding, newline="") as stream:
                    reader = csv.reader(stream, delimiter=delimiter, strict=True)
                    current = next((r for r in reader if r), None)
                    if current is None:
                        continue
                    if header is None:
                        header = current
                        if keep_header:
                            writer.writerow(header)
                    elif current != header:
                        raise ValueError(f"Header or column order differs:\n{path}")
                    for row in reader:
                        if cancel.is_set():
                            raise Cancelled()
                        if not row:
                            continue
                        if len(row) != len(header):
                            raise ValueError(f"Wrong column count in {path.name}, "
                                             f"near physical line {reader.line_num}.")
                        writer.writerow(row)
                        count += 1
                        if count % 50000 == 0:
                            notify(f"File {index}/{len(files)} | {count:,} rows written")
            if header is None:
                raise ValueError("All selected files are empty.")
        if cancel.is_set():
            raise Cancelled()
        os.replace(temp, output)
        return count
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


class App(tk.Tk if tk is not None else object):
    def __init__(self):
        super().__init__()
        self.title("CSV Merger")
        self.geometry("850x540")
        self.minsize(650, 400)
        self.files = []
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.controls = []
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Add files repeatedly to collect CSVs from different folders.").pack(anchor="w")
        bar = ttk.Frame(frame); bar.pack(fill="x", pady=8)
        for label, command in [("Add files...", self.add), ("Remove selected", self.remove),
                               ("Clear", self.clear), ("Move up", lambda: self.move(-1)),
                               ("Move down", lambda: self.move(1))]:
            b = ttk.Button(bar, text=label, command=command)
            b.pack(side="left", padx=(0, 5)); self.controls.append(b)
        box = ttk.Frame(frame); box.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(box, selectmode="extended", exportselection=False)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.listbox.yview)
        horizontal = ttk.Scrollbar(box, orient="horizontal", command=self.listbox.xview)
        self.listbox.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        box.columnconfigure(0, weight=1); box.rowconfigure(0, weight=1)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns"); horizontal.grid(row=1, column=0, sticky="ew")
        opts = ttk.Frame(frame); opts.pack(fill="x", pady=10)
        ttk.Label(opts, text="Separator:").pack(side="left")
        self.sep = ttk.Combobox(opts, values=["Comma", "Semicolon", "Tab"], state="readonly", width=12)
        self.sep.set("Comma"); self.sep.pack(side="left", padx=6)
        ttk.Label(opts, text="Input encoding:").pack(side="left")
        self.encoding = ttk.Combobox(opts, values=["utf-8-sig", "cp1252", "utf-16"], state="readonly", width=12)
        self.encoding.set("utf-8-sig"); self.encoding.pack(side="left", padx=6)
        self.keep = tk.BooleanVar(value=True)
        check = ttk.Checkbutton(frame, text="Keep one header (uncheck to remove all headers)", variable=self.keep)
        check.pack(anchor="w"); self.controls.append(check)
        row = ttk.Frame(frame); row.pack(fill="x", pady=10)
        b = ttk.Button(row, text="Merge / choose output...", command=self.start)
        b.pack(side="left"); self.controls.append(b)
        self.stop = ttk.Button(row, text="Cancel", command=self.cancel.set, state="disabled")
        self.stop.pack(side="left", padx=8)
        self.status = tk.StringVar(value="No files selected.")
        ttk.Label(frame, textvariable=self.status, wraplength=780).pack(anchor="w")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self.poll)

    def refresh(self, selected=()):
        self.listbox.delete(0, "end")
        for path in self.files:
            self.listbox.insert("end", str(path))
        for index in selected:
            self.listbox.selection_set(index)
        self.status.set(f"{len(self.files)} files selected. Merge order = displayed order.")

    def add(self):
        paths = filedialog.askopenfilenames(parent=self, title="Add CSV files (repeat for other folders)",
                    filetypes=[("CSV / TSV", "*.csv *.tsv *.txt"), ("All files", "*.*")])
        for item in paths:
            path = Path(item).resolve()
            if path not in self.files:
                self.files.append(path)
        self.refresh()

    def remove(self):
        for index in reversed(self.listbox.curselection()):
            del self.files[index]
        self.refresh()

    def clear(self):
        self.files.clear(); self.refresh()

    def move(self, step):
        indices = list(self.listbox.curselection())
        if not indices or min(indices) + step < 0 or max(indices) + step >= len(self.files):
            return
        for i in (indices if step < 0 else reversed(indices)):
            self.files[i], self.files[i + step] = self.files[i + step], self.files[i]
        self.refresh([i + step for i in indices])

    def set_busy(self, value):
        self.busy = value
        for control in self.controls:
            control.configure(state="disabled" if value else "normal")
        for control in (self.sep, self.encoding):
            control.configure(state="disabled" if value else "readonly")
        self.stop.configure(state="normal" if value else "disabled")

    def start(self):
        if not self.files:
            messagebox.showwarning("No files", "Add input files first."); return
        output = filedialog.asksaveasfilename(parent=self, title="Choose output file",
                    defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not output:
            return
        settings = (tuple(self.files), output,
                    {"Comma": ",", "Semicolon": ";", "Tab": "\t"}[self.sep.get()],
                    self.encoding.get(), self.keep.get())
        self.cancel.clear(); self.set_busy(True)
        threading.Thread(target=self.worker, args=settings, daemon=True).start()

    def worker(self, files, output, delimiter, encoding, keep):
        try:
            count = merge_csv(files, output, delimiter, encoding, keep, self.cancel,
                              lambda msg: self.events.put(("status", msg)))
            self.events.put(("done", f"Merged {count:,} data rows.\n{output}"))
        except Cancelled:
            self.events.put(("cancelled", "Cancelled. Temporary output removed."))
        except Exception as exc:
            self.events.put(("error", f"{type(exc).__name__}: {exc}"))

    def poll(self):
        try:
            while True:
                kind, text = self.events.get_nowait()
                self.status.set(text)
                if kind != "status":
                    self.set_busy(False)
                    if kind == "error":
                        messagebox.showerror("Merge failed", text)
                    elif kind == "done":
                        messagebox.showinfo("Complete", text)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def close(self):
        if self.busy:
            self.cancel.set()
            messagebox.showinfo("Cancelling", "Cancellation requested. Wait for processing to stop, then close.")
        else:
            self.destroy()


if __name__ == "__main__":
    limit = sys.maxsize
    while True:
        try:
            csv.field_size_limit(limit)
            break
        except OverflowError:
            limit //= 10
    if tk is None:
        raise SystemExit("Tkinter is missing. Use a Python installation with Tcl/Tk support.")
    App().mainloop()