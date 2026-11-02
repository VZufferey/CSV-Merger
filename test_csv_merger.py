import csv
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from csv_merger import merge_csv, Cancelled


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / "a.csv"
        self.b = self.root / "b.csv"
        self.output = self.root / "out.csv"
        self.a.write_text("id,value\n1,hello\n", encoding="utf-8")
        self.b.write_text("id,value\n2,world\n", encoding="utf-8")

    def assert_clean(self):
        self.assertEqual(list(self.root.glob(".csv-merge-*.tmp")), [])

    def test_each_input_opened_once(self):
        original = Path.open
        opened = []
        def tracked(path, *args, **kwargs):
            if path in (self.a, self.b):
                opened.append(path)
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", tracked):
            self.assertEqual(merge_csv([self.a, self.b], self.output), 2)
        self.assertEqual(opened, [self.a, self.b])
        self.assert_clean()

    def test_overwrite(self):
        self.output.write_text("old", encoding="utf-8")
        merge_csv([self.a, self.b], self.output)
        self.assertIn("2,world", self.output.read_text(encoding="utf-8-sig"))

    def test_failure_preserves_existing_output(self):
        for bad in ("value,id\nworld,2\n", "id,value\n2,world,extra\n",
                    'id,value\n2,"unclosed\n'):
            with self.subTest(bad=bad):
                self.output.write_text("old", encoding="utf-8")
                self.b.write_text(bad, encoding="utf-8")
                with self.assertRaises((ValueError, csv.Error)):
                    merge_csv([self.a, self.b], self.output)
                self.assertEqual(self.output.read_text(), "old")
                self.assert_clean()

    def test_input_protected(self):
        before = self.a.read_bytes()
        with self.assertRaises(ValueError):
            merge_csv([self.a], self.a)
        self.assertEqual(self.a.read_bytes(), before)

    def test_empty_inputs(self):
        self.a.write_text("\n\n")
        self.b.write_text("")
        with self.assertRaises(ValueError):
            merge_csv([self.a, self.b], self.output)
        self.assertFalse(self.output.exists())
        self.assert_clean()

    def test_empty_file_skipped_headerless_output(self):
        self.a.write_text("")
        self.assertEqual(merge_csv([self.a, self.b], self.output, keep_header=False), 1)
        self.assertEqual(self.output.read_text(encoding="utf-8-sig").strip(), "2,world")

    def test_multifolder_bom_multiline(self):
        folder = self.root / "elsewhere"; folder.mkdir()
        other = folder / "a.csv"
        with other.open("w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows([["id", "value"], ["3", "a,b\nnext line"]])
        merge_csv([self.a, other], self.output)
        with self.output.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[-1], ["3", "a,b\nnext line"])

    def test_cancellation_cleanup(self):
        cancel = threading.Event()
        self.output.write_text("old")
        def notify(text):
            cancel.set()
        with self.assertRaises(Cancelled):
            merge_csv([self.a], self.output, cancel=cancel, notify=notify)
        self.assertEqual(self.output.read_text(), "old")
        self.assert_clean()


if __name__ == "__main__":
    unittest.main()