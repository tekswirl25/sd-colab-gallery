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


class LinkQueryTest(unittest.TestCase):
    MODES = ("text2img", "img2img", "controlnet", "inpaint", "upscale")

    def test_parse_valid_query(self):
        q = gallery_data.parse_link_query({"mode": "text2img", "img": "text2img_20261030_100000"}, self.MODES)
        self.assertEqual(q, ("text2img", "text2img_20261030_100000"))

    def test_unknown_mode_or_missing_parts_give_none(self):
        self.assertIsNone(gallery_data.parse_link_query({"mode": "evil", "img": "x"}, self.MODES))
        self.assertIsNone(gallery_data.parse_link_query({"mode": "text2img"}, self.MODES))
        self.assertIsNone(gallery_data.parse_link_query({}, self.MODES))
        self.assertIsNone(gallery_data.parse_link_query(None, self.MODES))

    def test_image_name_is_sanitised(self):
        # в имени допустимы только буквы, цифры, подчёркивание, дефис и точка: никаких путей
        self.assertIsNone(gallery_data.parse_link_query({"mode": "text2img", "img": "../../etc/passwd"}, self.MODES))
        self.assertIsNone(gallery_data.parse_link_query({"mode": "text2img", "img": "a/b"}, self.MODES))

    def test_find_item_by_name_with_or_without_extension(self):
        items = [{"name": "b"}, {"name": "a"}]
        self.assertEqual(gallery_data.find_item(items, "a"), 1)
        self.assertEqual(gallery_data.find_item(items, "a.png"), 1)
        self.assertIsNone(gallery_data.find_item(items, "zzz"))


class ViewerDataTest(GalleryDataTest):
    """Просмотр без файлового сервера Gradio: картинки встроены в страницу, листание, удаление."""

    def items3(self):
        self.add("a_20261103_100000", {"seed": 1, "prompt": "p1"})
        self.add("a_20261103_110000", {"seed": 2, "prompt": "p2"})
        self.add("a_20261103_120000", {"seed": 3, "prompt": "p3"})
        return gallery_data.list_items(self.dir)  # новые первыми: 12, 11, 10

    def test_grid_embeds_every_thumbnail_and_its_caption(self):
        html = gallery_data.grid_html(self.items3())
        self.assertEqual(html.count("data:image/jpeg;base64,"), 3)
        self.assertIn("seed 3", html)
        self.assertLess(html.index("seed 3"), html.index("seed 1"))  # новые первыми

    def test_grid_without_items_says_so_and_has_no_image(self):
        html = gallery_data.grid_html([])
        self.assertNotIn("<img", html)
        self.assertTrue(html)

    def test_grid_shows_only_the_latest_limit_and_tells_about_the_rest(self):
        html = gallery_data.grid_html(self.items3(), limit=2)
        self.assertEqual(html.count("<img"), 2)
        self.assertIn("1", html.split("<img")[-1])  # сколько не показано

    def test_grid_without_a_thumbnail_file_uses_the_original(self):
        self.add("b_20261103_130000", {"seed": 5}, thumb=False)
        html = gallery_data.grid_html(gallery_data.list_items(self.dir))
        self.assertIn("data:image/jpeg;base64,", html)

    def test_captions_are_escaped(self):
        self.add("c_20261103_140000", {"seed": "<b>1</b>"})
        html = gallery_data.grid_html(gallery_data.list_items(self.dir))
        self.assertNotIn("<b>1</b>", html)

    def test_view_embeds_a_big_preview_and_a_download_of_the_original(self):
        item = self.items3()[0]
        html = gallery_data.view_html(item)
        self.assertIn("data:image/jpeg;base64,", html)  # крупный просмотр
        self.assertIn('download="a_20261103_120000.png"', html)
        self.assertIn("data:image/png;base64,", html)  # оригинал без изменений

    def test_view_preview_is_limited_in_size_and_the_original_is_not_touched(self):
        import base64
        import io
        Image.new("RGB", (2000, 1000), "red").save(os.path.join(self.dir, "big_20261103_150000.png"))
        item = gallery_data.list_items(self.dir)[0]
        html = gallery_data.view_html(item, preview_side=512)
        b64 = html.split("data:image/jpeg;base64,")[1].split('"')[0]
        self.assertEqual(max(Image.open(io.BytesIO(base64.b64decode(b64))).size), 512)
        self.assertEqual(Image.open(item["image"]).size, (2000, 1000))

    def test_view_of_nothing_is_empty(self):
        self.assertEqual(gallery_data.view_html(None), "")

    def test_choices_are_caption_and_name_newest_first(self):
        ch = gallery_data.choices(self.items3())
        self.assertEqual(ch[0][1], "a_20261103_120000")
        self.assertIn("seed 3", ch[0][0])
        self.assertEqual(len(ch), 3)

    def test_grid_numbers_the_frames_so_they_can_be_ticked_in_the_list(self):
        html = gallery_data.grid_html(self.items3())
        self.assertLess(html.index("1."), html.index("2."))
        self.assertIn("3.", html)

    def test_tick_choices_carry_the_same_numbers_as_the_grid(self):
        ch = gallery_data.tick_choices(self.items3())
        self.assertEqual([v for _, v in ch],
                         ["a_20261103_120000", "a_20261103_110000", "a_20261103_100000"])
        self.assertTrue(ch[0][0].startswith("1."))
        self.assertTrue(ch[2][0].startswith("3."))
        self.assertIn("seed 3", ch[0][0])

    def test_css_puts_each_tick_under_its_thumbnail(self):
        css = gallery_data.ticks_css(["text2img", "upscale"], thumb_side=256, gap=8)
        for key in ("text2img", "upscale"):
            self.assertIn(f"#{key}_ticks", css)
        self.assertIn("flex-wrap: wrap", css)
        self.assertIn("gap: 8px", css)          # промежуток как в сетке миниатюр
        self.assertIn("width: 256px", css)      # ширина галочки как у миниатюры

    def test_grid_uses_the_same_width_and_gap_as_the_css(self):
        html = gallery_data.grid_html(self.items3(), thumb_side=200, gap=5)
        self.assertIn("width:200px", html)
        self.assertIn("gap:5px", html)

    def test_delete_many_removes_only_the_ticked_frames(self):
        items = self.items3()
        n = gallery_data.delete_many(items, ["a_20261103_120000", "a_20261103_100000"])
        self.assertEqual(n, 2)
        self.assertEqual(sorted(f for f in os.listdir(self.dir) if f.endswith(".png")), ["a_20261103_110000.png"])
        self.assertFalse(os.path.exists(os.path.join(self.dir, "a_20261103_120000.png.json")))

    def test_delete_many_ignores_unknown_and_unsafe_names_and_empty_ticks(self):
        items = self.items3()
        self.assertEqual(gallery_data.delete_many(items, ["nope", "../x", None]), 0)
        self.assertEqual(gallery_data.delete_many(items, []), 0)
        self.assertEqual(len([f for f in os.listdir(self.dir) if f.endswith(".png")]), 3)

    def test_neighbor_steps_and_wraps_around(self):
        items = self.items3()
        self.assertEqual(gallery_data.neighbor(items, "a_20261103_120000", +1), "a_20261103_110000")
        self.assertEqual(gallery_data.neighbor(items, "a_20261103_120000", -1), "a_20261103_100000")  # по кругу
        self.assertEqual(gallery_data.neighbor(items, "a_20261103_100000", +1), "a_20261103_120000")

    def test_neighbor_with_unknown_or_no_selection_gives_the_first_item(self):
        items = self.items3()
        self.assertEqual(gallery_data.neighbor(items, None, +1), "a_20261103_120000")
        self.assertEqual(gallery_data.neighbor(items, "zzz", -1), "a_20261103_120000")
        self.assertIsNone(gallery_data.neighbor([], None, +1))

    def test_delete_one_removes_image_metadata_and_thumbnail_only_of_that_item(self):
        items = self.items3()
        self.assertTrue(gallery_data.delete_one(items, "a_20261103_110000"))
        left = sorted(os.listdir(self.dir))
        self.assertNotIn("a_20261103_110000.png", left)
        self.assertNotIn("a_20261103_110000.png.json", left)
        self.assertFalse(os.path.exists(os.path.join(self.root, "thumbnails", "text2img", "a_20261103_110000.jpg")))
        self.assertIn("a_20261103_120000.png", left)
        self.assertIn("a_20261103_100000.png.json", left)

    def test_delete_one_of_an_unknown_name_deletes_nothing(self):
        items = self.items3()
        self.assertFalse(gallery_data.delete_one(items, "nope"))
        self.assertFalse(gallery_data.delete_one(items, "../x"))
        self.assertEqual(len([f for f in os.listdir(self.dir) if f.endswith(".png")]), 3)

    def test_delete_all_removes_images_metadata_and_thumbnails(self):
        items = self.items3()
        self.assertEqual(gallery_data.delete_all(items), 3)
        self.assertEqual(os.listdir(self.dir), [])
        self.assertEqual(os.listdir(os.path.join(self.root, "thumbnails", "text2img")), [])


if __name__ == "__main__":
    unittest.main()
