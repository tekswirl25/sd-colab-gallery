import os
import sys
import tempfile
import types
import unittest

from tests import stubs

stubs.install()
# gallery_manager тянет scripts.utils (cv2, torch) — для этих тестов нужен только list_images
utils = types.ModuleType("scripts.utils")
utils.list_images = lambda folder: []
sys.modules.setdefault("scripts.utils", utils)

from scripts import gallery_manager  # noqa: E402


class ShowGalleryTest(unittest.TestCase):
    def test_returns_only_images_sorted(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("b.png", "a.JPG", "c.webp", "d.json", "e.txt"):
                open(os.path.join(d, name), "w").close()
            got = [os.path.basename(p) for p in gallery_manager.show_gallery(d)]
            self.assertEqual(got, ["a.JPG", "b.png", "c.webp"])

    def test_missing_folder_gives_empty_list(self):
        # папка вкладки (например inpaint) может быть ещё не создана
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(gallery_manager.show_gallery(os.path.join(d, "nope")), [])


if __name__ == "__main__":
    unittest.main()
