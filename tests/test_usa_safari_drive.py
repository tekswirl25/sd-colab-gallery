import os
import tempfile
import unittest

from tests import stubs

stubs.install()
from scripts import usa_safari, usa_safari_drive  # noqa: E402


class SetupDriveReferenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "USA Safari Reference")

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_the_four_folders_and_seeds_log(self):
        r = usa_safari_drive.setup_drive_reference(self.root)
        for name in ("characters", "style", "seeds", "episodes"):
            self.assertTrue(os.path.isdir(os.path.join(self.root, name)), name)
        log = os.path.join(self.root, "seeds", "seeds_log.txt")
        self.assertEqual(r["seeds_log"], log)
        self.assertTrue(r["seeds_log_created"])
        with open(log, encoding="utf-8") as f:
            self.assertIn("Seeds Log", f.read())

    def test_second_run_changes_nothing(self):
        usa_safari_drive.setup_drive_reference(self.root)
        log = os.path.join(self.root, "seeds", "seeds_log.txt")
        with open(log, "a", encoding="utf-8") as f:
            f.write("[2026] seed=1 | mode=x | file=y\n")
        r = usa_safari_drive.setup_drive_reference(self.root)
        self.assertFalse(r["seeds_log_created"])
        with open(log, encoding="utf-8") as f:
            self.assertIn("seed=1", f.read())  # записи не затираются

    def test_report_text_lists_folders_and_log_status(self):
        text = usa_safari_drive.format_setup(usa_safari_drive.setup_drive_reference(self.root))
        for name in ("characters", "style", "seeds", "episodes"):
            self.assertIn(name, text)
        self.assertIn("создан", text)
        again = usa_safari_drive.format_setup(usa_safari_drive.setup_drive_reference(self.root))
        self.assertIn("уже существует", again)

    def test_default_root_is_shared_with_seed_log_and_ui(self):
        # одно место для пути: seeds_log в usa_safari лежит под тем же корнем.
        # Свежий импорт: другие тесты подменяют SEEDS_LOG у общего экземпляра.
        import importlib
        import sys
        sys.modules.pop("scripts.usa_safari", None)
        fresh = importlib.import_module("scripts.usa_safari")
        self.assertEqual(os.path.dirname(os.path.dirname(str(fresh.SEEDS_LOG))), str(fresh.REFERENCE_ROOT))
        self.assertEqual(usa_safari_drive.default_root(), str(fresh.REFERENCE_ROOT))


if __name__ == "__main__":
    unittest.main()
