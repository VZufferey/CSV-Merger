# CSV Merger

Small local graphical CSV merger. One Python script, no third-party packages,
no Conda, no virtual environment, no setup command. Data never leaves your computer.

## Requirements

Python 3.10 or later with Tkinter. The normal python.org Windows installation
includes Tkinter; keep the Tcl/Tk option enabled. Python itself IS required:
this is a source script, not a standalone executable.

## Start

Windows: double-click `start_windows.bat`.
Alternatively, from the project folder:

```text
python csv_merger.py
```

The launcher tries `py -3`, then `python`. If your Python installation does not
include Tkinter, `python -m tkinter` will fail; use a Python installation that
includes it. No pip commands are needed.

## Use

1. Click **Add files...**, select CSVs, and confirm.
2. Click **Add files... again** to add CSVs from another folder. Repeat as needed.
   Existing selections are kept; duplicate paths are ignored.
3. Review full paths. Remove files or move selections up/down to choose merge order.
4. Choose the separator and input encoding shared by ALL selected files.
5. Keep the header checkbox enabled for one output header. Disable it to remove all headers.
6. Click **Merge / choose output...** and choose a NEW output filename.

Inputs can be anywhere accessible to the computer. They do not need to share a folder.
Order is the displayed order, not necessarily alphabetical. Within one file-picker
selection, the operating system controls the initial order.

## Input rules

- Every nonempty input has one header record, including when output headers are disabled.
- Headers must match exactly, including column order, whitespace and case.
- This is concatenation, not a database join: no sorting or deduplication of data rows.
- Empty files and blank records are skipped. Rows consisting of empty fields are retained.
- Every data record must have the same number of fields as the header.
- Standard CSV quoting is supported, including quoted delimiters and multiline fields.
- Repeated headers INSIDE a file are not removed.
- Do not modify input files while a merge is running.

## Large files and safety

Records are streamed, not loaded into a DataFrame. Memory depends on the largest
record, not on the complete dataset. Progress reports files and every 50,000 data
rows; it is not a byte-level percentage. Processing runs in a background thread.
Cancel is checked between records; cancellation may wait for a large record or slow I/O.

Headers are checked first. Output is written to a temporary file in the destination
folder and published only after success.
Normal errors and cancellation remove the temporary output. Forced termination or
power loss may leave a `.csv-merge-*.tmp` file, which can be deleted after the app stops.
Publication uses a hard link to avoid overwriting an output created concurrently.
The destination filesystem must support hard links (normal local Windows NTFS does).
On filesystems that do not support this, merging fails safely; choose a local NTFS
folder and move the completed CSV afterwards. You need disk space for the merged file.

Output uses UTF-8 with BOM and the selected separator. Field values remain strings;
quoting and line endings may change. No numeric or date inference is performed.
Opening the result in Excel may nevertheless trigger Excel's own conversions.

## Files

- `csv_merger.py`: application and merge logic.
- `start_windows.bat`: optional Windows convenience launcher.
- `test_csv_merger.py`: standard-library merge tests (no GUI required).
- `.gitignore`: excludes caches, temporary merge files, and build directories.

Run tests with `python -m unittest -v test_csv_merger.py`.
No `requirements.txt` or `manage.py` is necessary.

## License

No license is selected in this starter project. Add a LICENSE file (for example MIT)
if you intend to publish it as open-source.
