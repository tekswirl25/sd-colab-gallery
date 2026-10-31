import os
import sys
import tempfile
import unittest

from tests import stubs
from tests.test_usa_safari_ui import fake_display, fake_widgets

stubs.install()
from scripts import notebook_uploads  # noqa: E402


class UploadsTest(unittest.TestCase):
    def setUp(self):
        notebook_uploads.PATHS.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.disp = fake_display()

    def tearDown(self):
        notebook_uploads.PATHS.clear()
        self.tmp.cleanup()

    def show(self, kind):
        return notebook_uploads.show_upload(kind, upload_dir=self.tmp.name, widgets=fake_widgets(),
                                            ipy_display=self.disp)

    def test_all_four_kinds_exist_with_hints(self):
        self.assertEqual(set(notebook_uploads.KINDS), {"img2img", "controlnet", "inpaint_image", "inpaint_mask"})
        for kind in notebook_uploads.KINDS:
            self.show(kind)
            self.assertTrue(self.disp.shown)

    def test_upload_saves_file_and_fills_path_box(self):
        ui = self.show("img2img")
        ui.upload_btn.value = ({"name": "a.png", "content": b"abc"},)
        dest = os.path.join(self.tmp.name, "a.png")
        self.assertEqual(ui.path_box.value, dest)
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), b"abc")
        self.assertIn("a.png", ui.status_out.text)

    def test_old_ipywidgets_dict_format(self):
        ui = self.show("img2img")
        ui.upload_btn.value = {"b.png": {"content": b"xy"}}
        self.assertEqual(ui.path_box.value, os.path.join(self.tmp.name, "b.png"))

    def test_confirm_stores_path_under_the_kind_only(self):
        p = os.path.join(self.tmp.name, "c.png")
        open(p, "wb").write(b"1")
        ui = self.show("controlnet")
        ui.path_box.value = p
        ui.confirm_btn.click()
        self.assertEqual(notebook_uploads.get_path("controlnet"), p)
        self.assertIsNone(notebook_uploads.get_path("img2img"))
        self.assertIn("control_path", ui.status_out.text)

    def test_confirm_with_missing_file_warns_and_keeps_nothing_new(self):
        ui = self.show("inpaint_mask")
        ui.path_box.value = os.path.join(self.tmp.name, "nope.png")
        ui.confirm_btn.click()
        self.assertIn("не найден", ui.status_out.text)
        self.assertNotIn("inpaint_mask", notebook_uploads.PATHS)

    def test_unknown_kind_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "nope"):
            self.show("nope")


if __name__ == "__main__":
    unittest.main()
