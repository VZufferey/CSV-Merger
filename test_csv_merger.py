import csv
import tempfile
import threading
import unittest
from pathlib import Path
from csv_merger import merge_csv, Cancelled

class MergeTests(unittest.TestCase):
    def test_merge_multifolder_multiline_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for i in range(2):
                folder = root / str(i); folder.mkdir()
                path = folder / "input.csv"
                with path.open("w", encoding="utf-8-sig", newline="") as f:
                    csv.writer(f).writerows([["id", "text"], [str(i), "quoted, text\nand newline"]])
                paths.append(path)
            output = root / "out.csv"
            self.assertEqual(merge_csv(paths, output), 2)
            with output.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[2][1], "quoted, text\nand newline")
            self.assertEqual(merge_csv(paths, output), 2)

    def test_headerless_output_and_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); a = root / "a.csv"; b = root / "b.csv"
            a.write_text("x;y\n1;2\n", encoding="utf-8")
            output = root / "out.csv"
            merge_csv([a], output, delimiter=";", keep_header=False)
            self.assertEqual(output.read_text(encoding="utf-8-sig").strip(), "1;2")
            b.write_text("x;y\n3;4;5\n", encoding="utf-8")
            failed = root / "failed.csv"
            with self.assertRaises(ValueError):
                merge_csv([a, b], failed, delimiter=";")
            self.assertFalse(failed.exists())
            self.assertEqual(list(root.glob(".csv-merge-*.tmp")), [])
            b.write_text("different;header\n3;4\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                merge_csv([a, b], failed, delimiter=";")
            cancel = threading.Event(); cancel.set()
            with self.assertRaises(Cancelled):
                merge_csv([a], failed, cancel=cancel)

if __name__ == "__main__":
    unittest.main()
