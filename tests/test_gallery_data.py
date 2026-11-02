import json
import os
import tempfile
import unittest

from PIL import Image

from tests import stubs

stubs.install()
from scripts import gallery_data  # noqa: E402


class GalleryDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.dir = os.path.join(self.root, "text2img")
        os.makedirs(self.dir)
        os.makedirs(os.path.join(self.root, "thumbnails", "text2img"))

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name, meta=None, thumb=True):
        Image.new("RGB", (40, 30), "white").save(os.path.join(self.dir, name + ".png"))
        if meta is not None:
            with open(os.path.join(self.dir, name + ".png.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
        if thumb:
            Image.new("RGB", (10, 8), "gray").save(os.path.join(self.root, "thumbnails", "text2img", name + ".jpg"))

    def test_newest_first_and_only_images(self):
        self.add("text2img_20261030_100000", {"seed": 11})
        self.add("text2img_20261030_110000", {"seed": 12})
        open(os.path.join(self.dir, "notes.txt"), "w").close()
        names = [os.path.basename(i["image"]) for i in gallery_data.list_items(self.dir)]
        self.assertEqual(names, ["text2img_20261030_110000.png", "text2img_20261030_100000.png"])

    def test_caption_has_seed_and_time(self):
        self.add("text2img_20261030_100000", {"seed": 11, "prompt": "a cat"})
        item = gallery_data.list_items(self.dir)[0]
        self.assertEqual(item["seed"], 11)
        self.assertIn("seed 11", item["caption"])
        self.assertIn("20261030_100000", item["caption"])

    def test_item_without_json_still_listed_with_name_caption(self):
        self.add("text2img_20261030_100000", None)
        item = gallery_data.list_items(self.dir)[0]
        self.assertIsNone(item["seed"])
        self.assertEqual(item["caption"], "text2img_20261030_100000")

    def test_thumbnail_path_found_or_none(self):
        self.add("text2img_20261030_100000", {"seed": 1})
        self.add("text2img_20261030_110000", {"seed": 2}, thumb=False)
        by = {os.path.basename(i["image"]): i for i in gallery_data.list_items(self.dir)}
        self.assertTrue(by["text2img_20261030_100000.png"]["thumb"].endswith("text2img_20261030_100000.jpg"))
        self.assertIsNone(by["text2img_20261030_110000.png"]["thumb"])

    def test_broken_json_is_not_fatal(self):
        self.add("text2img_20261030_100000", None)
        with open(os.path.join(self.dir, "text2img_20261030_100000.png.json"), "w") as f:
            f.write("{not json")
        item = gallery_data.list_items(self.dir)[0]
        self.assertIsNone(item["seed"])

    def test_missing_folder_gives_empty_list(self):
        self.assertEqual(gallery_data.list_items(os.path.join(self.root, "nope")), [])

    def test_details_for_copying_and_download(self):
        self.add("text2img_20261030_100000", {"seed": 11, "prompt": "a cat", "steps": 30, "negative": "anime"})
        item = gallery_data.list_items(self.dir)[0]
        d = gallery_data.item_details(item)
        self.assertEqual(d["seed"], "11")
        self.assertEqual(d["prompt"], "a cat")
        self.assertIn('"steps": 30', d["params"])
        self.assertEqual(d["file"], item["image"])

    def test_details_without_meta_are_empty_but_have_the_file(self):
        self.add("text2img_20261030_100000", None)
        d = gallery_data.item_details(gallery_data.list_items(self.dir)[0])
        self.assertEqual((d["seed"], d["prompt"], d["params"]), ("", "", ""))
        self.assertTrue(d["file"].endswith(".png"))

    def test_details_for_no_selection(self):
        d = gallery_data.item_details(None)
        self.assertEqual((d["seed"], d["prompt"], d["params"], d["file"]), ("", "", "", None))


if __name__ == "__main__":
    unittest.main()
