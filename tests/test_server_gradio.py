import importlib
import json
import os
import sys
import tempfile
import types
import unittest

from PIL import Image

from tests import stubs

stubs.install()


# ---- заглушка gradio: запоминает компоненты и обработчики, ничего не запускает ----
class Comp:
    registry = []
    reject_copy_button = False

    def __init__(self, *args, **kw):
        if self.reject_copy_button and "show_copy_button" in kw and type(self).__name__ == "Textbox":
            raise TypeError("unexpected keyword show_copy_button")
        self.args, self.kw, self.handlers = args, kw, []
        Comp.registry.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def _on(kind):
        def reg(self, fn=None, inputs=None, outputs=None, **kw):
            self.handlers.append((kind, fn, inputs, outputs))
            return self
        return reg

    click = _on("click")
    load = _on("load")
    select = _on("select")
    then = _on("then")

    def launch(self, **kw):
        self.launched = kw


def fake_gradio():
    m = types.ModuleType("gradio")
    for name in ("Blocks", "Tab", "Tabs", "Row", "Gallery", "Button", "Checkbox", "Textbox", "File", "State", "Markdown"):
        setattr(m, name, type(name, (Comp,), {}))
    m.update = lambda **kw: ("update", kw)
    m.skip = lambda: ("skip", {})
    m.Request = type("Request", (), {})
    m.SelectData = type("SelectData", (), {"__init__": lambda self, index=None: setattr(self, "index", index)})
    return m


class ServerTest(unittest.TestCase):
    def setUp(self):
        Comp.registry = []
        Comp.reject_copy_button = False
        self.tmp = tempfile.TemporaryDirectory()
        self.out = self.tmp.name
        self.gr = fake_gradio()
        sys.modules["gradio"] = self.gr
        utils = types.ModuleType("scripts.utils")
        utils.list_images = lambda folder: []
        sys.modules["scripts.utils"] = utils
        for k in ("scripts.server_gradio", "scripts.gallery_manager"):
            sys.modules.pop(k, None)
        self.mod = importlib.import_module("scripts.server_gradio")

    def tearDown(self):
        for k in ("gradio", "scripts.utils", "scripts.server_gradio", "scripts.gallery_manager"):
            sys.modules.pop(k, None)
        self.tmp.cleanup()

    def add_image(self, mode, name, meta=None):
        d = os.path.join(self.out, mode)
        os.makedirs(d, exist_ok=True)
        os.makedirs(os.path.join(self.out, "thumbnails", mode), exist_ok=True)
        Image.new("RGB", (64, 48), "white").save(os.path.join(d, name + ".png"))
        Image.new("RGB", (16, 12), "gray").save(os.path.join(self.out, "thumbnails", mode, name + ".jpg"))
        if meta is not None:
            with open(os.path.join(d, name + ".png.json"), "w", encoding="utf-8") as f:
                json.dump(meta, f)

    def start(self):
        return self.mod.start_gradio_server(self.out, refresh_interval=5, LOG_LINES=10)

    def comps(self, kind, label=None):
        return [c for c in Comp.registry if type(c).__name__ == kind and (label is None or c.kw.get("label") == label)]

    def gallery(self, tab):
        return self.comps("Gallery", f"{tab} results")[0]

    def test_there_is_a_gallery_tab_for_every_mode_including_upscale(self):
        self.start()
        tabs = [c.args[0] for c in self.comps("Tab")]
        for name in ("Text2Img", "Img2Img", "ControlNet", "Inpaint", "Upscale"):
            self.assertIn(f"{name} Gallery", tabs)

    def test_gallery_shows_thumbnails_with_seed_captions_newest_first(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11, "prompt": "a cat"})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12, "prompt": "a dog"})
        self.start()
        value = self.gallery("Text2Img").kw["value"]
        self.assertEqual(len(value), 2)
        self.assertIn("seed 12", value[0][1])
        self.assertIn("seed 11", value[1][1])
        self.assertLessEqual(max(value[0][0].size), 256)  # миниатюра, не оригинал

    def test_selecting_an_image_gives_seed_prompt_params_and_the_original_file(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11, "prompt": "a cat", "steps": 30})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12, "prompt": "a dog"})
        self.start()
        gallery = self.gallery("Text2Img")
        (kind, fn, inputs, outputs), = [h for h in gallery.handlers if h[0] == "select"]
        state = self.comps("State")[0]
        self.assertIn(state, inputs)
        seed, prompt, params, file_path = fn(state.kw["value"], self.gr.SelectData(index=1))
        self.assertEqual((seed, prompt), ("11", "a cat"))
        self.assertIn('"steps": 30', params)
        self.assertTrue(file_path.endswith("text2img_20261030_100000.png"))
        self.assertTrue(os.path.exists(file_path))

    def test_detail_boxes_are_read_only_with_copy_buttons_and_a_download_file(self):
        self.start()
        for label in ("Seed", "Prompt", "Параметры"):
            box = self.comps("Textbox", label)[0]
            self.assertFalse(box.kw.get("interactive", True), label)
            self.assertTrue(box.kw.get("show_copy_button"), label)
        self.assertTrue(self.comps("File"))

    def test_server_still_builds_when_gradio_has_no_copy_button_option(self):
        Comp.reject_copy_button = True
        self.start()  # не должно упасть: ячейка с копированием откатывается на обычное поле
        self.assertTrue(self.comps("Textbox", "Seed"))

    def test_refresh_returns_gallery_and_fresh_items(self):
        self.start()
        self.add_image("text2img", "text2img_20261030_120000", {"seed": 99})
        refresh = next(c for c in self.comps("Button") if c.args and c.args[0] == "🔄 Refresh")
        # первая вкладка Text2Img: ищем кнопку этой вкладки по порядку создания
        text2img_refresh = [c for c in self.comps("Button") if c.args and c.args[0] == "🔄 Refresh"][0]
        (kind, fn, inputs, outputs), = text2img_refresh.handlers[:1]
        value, items = fn()
        self.assertIn("seed 99", value[0][1])
        self.assertEqual(items[0]["seed"], 99)

    def load_handler(self):
        demo = self.comps("Blocks")[0]
        (kind, fn, inputs, outputs), = [h for h in demo.handlers if h[0] == "load"]
        return fn, outputs

    def test_tabs_have_stable_ids_so_a_link_can_open_the_right_one(self):
        self.start()
        ids = [t.kw.get("id") for t in self.comps("Tab")]
        for key in ("text2img", "img2img", "controlnet", "inpaint", "upscale"):
            self.assertIn(key, ids)

    def test_link_opens_the_tab_and_the_image_details(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11, "prompt": "a cat"})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12, "prompt": "a dog"})
        self.start()
        fn, outputs = self.load_handler()
        req = types.SimpleNamespace(query_params={"mode": "text2img", "img": "text2img_20261030_100000"})
        res = fn(req)
        self.assertEqual(len(res), len(outputs))
        self.assertEqual(res[0], ("update", {"selected": "text2img"}))            # вкладка
        text2img = res[1:7]                                              # галерея, state, seed, prompt, params, file
        self.assertEqual(text2img[0][0], "update")
        self.assertEqual(text2img[0][1]["selected_index"], 1)            # вторая по порядку (новые первыми)
        self.assertEqual(len(text2img[0][1]["value"]), 2)                # галерея заодно обновилась
        self.assertEqual(len(text2img[1]), 2)                            # свежий список для выбора картинки
        self.assertEqual((text2img[2], text2img[3]), ("11", "a cat"))
        self.assertTrue(text2img[5].endswith("text2img_20261030_100000.png"))

    def test_link_to_an_unknown_image_or_mode_changes_nothing(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11})
        self.start()
        fn, outputs = self.load_handler()
        for query in ({"mode": "text2img", "img": "nope"}, {"mode": "evil", "img": "x"}, {}):
            res = fn(types.SimpleNamespace(query_params=query))
            self.assertEqual(len(res), len(outputs))
            self.assertTrue(all(r == ("skip", {}) for r in res), query)

    def test_delete_all_needs_confirmation(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 1})
        self.start()
        delete = [c for c in self.comps("Button") if c.args and c.args[0].endswith("Delete all")][0]
        (kind, fn, inputs, outputs) = delete.handlers[0]
        fn(False)
        self.assertTrue(os.path.exists(os.path.join(self.out, "text2img", "text2img_20261030_100000.png")))
        fn(True)
        self.assertFalse(os.path.exists(os.path.join(self.out, "text2img", "text2img_20261030_100000.png")))


if __name__ == "__main__":
    unittest.main()
