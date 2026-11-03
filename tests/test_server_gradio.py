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
    rejected_kwargs = ()  # параметры Textbox, которых эта (подставная) версия Gradio не знает

    def __init__(self, *args, **kw):
        if self.reject_copy_button and "show_copy_button" in kw and type(self).__name__ == "Textbox":
            raise TypeError("unexpected keyword show_copy_button")
        for bad in self.rejected_kwargs:
            if bad in kw and type(self).__name__ == "Textbox":
                raise TypeError(f"unexpected keyword {bad}")
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
    change = _on("change")
    then = _on("then")

    def launch(self, **kw):
        self.launched = kw


def fake_gradio():
    m = types.ModuleType("gradio")
    for name in ("Blocks", "Tab", "Tabs", "Row", "Gallery", "Button", "Checkbox", "Textbox", "File", "State", "Markdown", "HTML", "Dropdown"):
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
        Comp.rejected_kwargs = ()
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


    def test_the_start_report_names_the_gradio_version(self):
        # версия нужна, чтобы по выводу ячейки видеть, какой API у Gradio (6 заменил show_copy_button на buttons)
        import contextlib
        import io
        self.gr.__version__ = "6.2.0"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.start()
        self.assertIn("Gradio 6.2.0", buf.getvalue())

    def test_existing_files_are_loaded_at_start_and_the_report_names_the_folder_and_counts(self):
        # файлы, уже лежащие на Drive, видны сразу, до любой генерации; вывод показывает, какую папку смотрит галерея
        import contextlib
        import io
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 1})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 2})
        self.add_image("upscale", "upscale_20261030_100000", {"seed": 3})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.start()
        out = buf.getvalue()
        self.assertIn(self.out, out)
        self.assertIn("Text2Img: 2", out)
        self.assertIn("Upscale: 1", out)
        self.assertIn("Img2Img: 0", out)
        self.assertEqual(len(self.by_id("Dropdown", "text2img_pick").kw["choices"]), 2)

    def by_id(self, kind, elem_id):
        return [c for c in self.comps(kind) if c.kw.get("elem_id") == elem_id][0]

    def button(self, key, text):
        """Кнопка вкладки режима по тексту: кнопки создаются по порядку вкладок text2img, img2img, ..."""
        keys = ["text2img", "img2img", "controlnet", "inpaint", "upscale"]
        found = [c for c in self.comps("Button") if c.args and c.args[0] == text]
        return found[keys.index(key)]

    def png(self, mode, name):
        return os.path.join(self.out, mode, name + ".png")

    def test_there_is_a_gallery_tab_for_every_mode_including_upscale(self):
        self.start()
        tabs = [c.args[0] for c in self.comps("Tab")]
        for name in ("Text2Img", "Img2Img", "ControlNet", "Inpaint", "Upscale"):
            self.assertIn(f"{name} Gallery", tabs)

    def test_tabs_have_stable_ids_so_a_link_can_open_the_right_one(self):
        self.start()
        ids = [t.kw.get("id") for t in self.comps("Tab")]
        for key in ("text2img", "img2img", "controlnet", "inpaint", "upscale"):
            self.assertIn(key, ids)

    def test_no_component_depends_on_the_gradio_file_server(self):
        # Gallery, File и Image отдают картинки через файловый сервер Gradio, в Colab они приходят битыми
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 1})
        self.start()
        for kind in ("Gallery", "File", "Image"):
            self.assertEqual(self.comps(kind), [], kind)

    def test_grid_shows_embedded_thumbnails_newest_first(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11, "prompt": "a cat"})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12, "prompt": "a dog"})
        self.start()
        html = self.by_id("HTML", "text2img_grid").kw["value"]
        self.assertEqual(html.count("data:image/jpeg;base64,"), 2)
        self.assertLess(html.index("seed 12"), html.index("seed 11"))

    def test_picker_lists_every_frame_newest_first_and_starts_on_the_newest(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12})
        self.start()
        pick = self.by_id("Dropdown", "text2img_pick")
        self.assertEqual([v for _, v in pick.kw["choices"]], ["text2img_20261030_110000", "text2img_20261030_100000"])
        self.assertEqual(pick.kw["value"], "text2img_20261030_110000")

    def test_viewer_starts_on_the_newest_frame(self):
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12})
        self.start()
        self.assertIn("data:image/jpeg;base64,", self.by_id("HTML", "text2img_view").kw["value"])

    def handlers(self, comp, kind):
        return [h for h in comp.handlers if h[0] == kind]

    def test_choosing_a_frame_shows_it_with_seed_prompt_params_and_a_download(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11, "prompt": "a cat", "steps": 30})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12, "prompt": "a dog"})
        self.start()
        pick = self.by_id("Dropdown", "text2img_pick")
        (kind, fn, inputs, outputs), = self.handlers(pick, "change")
        state = self.comps("State")[0]
        self.assertIn(state, inputs)
        view, seed, prompt, params = fn(state.kw["value"], "text2img_20261030_100000")
        self.assertEqual((seed, prompt), ("11", "a cat"))
        self.assertIn('"steps": 30', params)
        self.assertIn('download="text2img_20261030_100000.png"', view)

    def test_choosing_nothing_clears_the_viewer(self):
        self.start()
        pick = self.by_id("Dropdown", "text2img_pick")
        (kind, fn, inputs, outputs), = self.handlers(pick, "change")
        self.assertEqual(fn([], None), ("", "", "", ""))

    def copy_kwargs(self, label):
        box = self.comps("Textbox", label)[0]
        return box.kw.get("buttons"), box.kw.get("show_copy_button")

    def test_detail_boxes_are_read_only_with_copy_buttons(self):
        self.start()
        for label in ("Seed", "Prompt", "Параметры"):
            box = self.comps("Textbox", label)[0]
            self.assertFalse(box.kw.get("interactive", True), label)
            self.assertEqual(self.copy_kwargs(label), (["copy"], None), label)  # Gradio 6: buttons=["copy"]

    def test_older_gradio_without_buttons_gets_show_copy_button(self):
        Comp.rejected_kwargs = ("buttons",)
        self.start()
        for label in ("Seed", "Prompt", "Параметры"):
            self.assertEqual(self.copy_kwargs(label), (None, True), label)

    def test_server_still_builds_when_gradio_has_no_copy_button_option(self):
        Comp.rejected_kwargs = ("buttons", "show_copy_button")
        self.start()  # не должно упасть: ячейка с копированием откатывается на обычное поле
        self.assertTrue(self.comps("Textbox", "Seed"))

    def test_next_and_previous_step_through_the_frames_one_after_another(self):
        for h in (10, 11, 12):
            self.add_image("text2img", f"text2img_20261030_{h}0000", {"seed": h})
        self.start()
        state = self.comps("State")[0].kw["value"]
        nxt = self.handlers(self.button("text2img", "Вперёд ▶"), "click")[0]
        prev = self.handlers(self.button("text2img", "◀ Назад"), "click")[0]
        self.assertEqual(nxt[1](state, "text2img_20261030_120000"), "text2img_20261030_110000")
        self.assertEqual(prev[1](state, "text2img_20261030_110000"), "text2img_20261030_120000")
        self.assertEqual(self.by_id("Dropdown", "text2img_pick"), nxt[3] if not isinstance(nxt[3], list) else nxt[3][0])

    def test_refresh_returns_fresh_grid_items_and_picker(self):
        self.start()
        self.add_image("text2img", "text2img_20261030_120000", {"seed": 99})
        (kind, fn, inputs, outputs), = self.handlers(self.button("text2img", "🔄 Refresh"), "click")
        grid, items, pick = fn()
        self.assertIn("seed 99", grid)
        self.assertEqual(items[0]["seed"], 99)
        self.assertEqual(pick[1]["value"], "text2img_20261030_120000")

    def test_delete_selected_needs_confirmation_and_removes_only_that_frame(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 1})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 2})
        self.start()
        state = self.comps("State")[0].kw["value"]
        (kind, fn, inputs, outputs), = self.handlers(self.button("text2img", "🗑️ Delete selected"), "click")
        fn(False, "text2img_20261030_110000", state)
        self.assertTrue(os.path.exists(self.png("text2img", "text2img_20261030_110000")))
        grid, items, pick, confirm = fn(True, "text2img_20261030_110000", state)
        self.assertFalse(os.path.exists(self.png("text2img", "text2img_20261030_110000")))
        self.assertFalse(os.path.exists(self.png("text2img", "text2img_20261030_110000") + ".json"))
        self.assertTrue(os.path.exists(self.png("text2img", "text2img_20261030_100000")))
        self.assertEqual([i["name"] for i in items], ["text2img_20261030_100000"])
        self.assertEqual(pick[1]["value"], "text2img_20261030_100000")  # просмотр переходит на соседний кадр
        self.assertFalse(confirm)  # подтверждение сбрасывается

    def test_delete_all_needs_confirmation(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 1})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 2})
        self.start()
        state = self.comps("State")[0].kw["value"]
        (kind, fn, inputs, outputs), = self.handlers(self.button("text2img", "🗑️ Delete all"), "click")
        fn(False, state)
        self.assertTrue(os.path.exists(self.png("text2img", "text2img_20261030_100000")))
        grid, items, pick, confirm = fn(True, state)
        self.assertEqual(items, [])
        self.assertFalse(os.path.exists(self.png("text2img", "text2img_20261030_100000")))
        self.assertIsNone(pick[1]["value"])

    def load_handler(self):
        demo = self.comps("Blocks")[0]
        found = [h for h in self.handlers(demo, "load") if isinstance(h[3], list) and len(h[3]) > 1]
        (kind, fn, inputs, outputs), = found
        return fn, outputs

    def test_link_opens_the_tab_and_selects_the_frame(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11, "prompt": "a cat"})
        self.add_image("text2img", "text2img_20261030_110000", {"seed": 12, "prompt": "a dog"})
        self.start()
        fn, outputs = self.load_handler()
        req = types.SimpleNamespace(query_params={"mode": "text2img", "img": "text2img_20261030_100000"})
        res = fn(req)
        self.assertEqual(len(res), len(outputs))
        self.assertEqual(res[0], ("update", {"selected": "text2img"}))
        pick = res[1]  # первые в группе режима: выбор кадра
        self.assertEqual(pick[1]["value"], "text2img_20261030_100000")
        group = res[1:8]  # pick, state, grid, view, seed, prompt, params
        self.assertEqual(len(group[1]), 2)
        self.assertIn("data:image/jpeg;base64,", group[3])
        self.assertEqual((group[4], group[5]), ("11", "a cat"))

    def test_link_to_an_unknown_image_or_mode_changes_nothing(self):
        self.add_image("text2img", "text2img_20261030_100000", {"seed": 11})
        self.start()
        fn, outputs = self.load_handler()
        for query in ({"mode": "text2img", "img": "nope"}, {"mode": "evil", "img": "x"}, {}):
            res = fn(types.SimpleNamespace(query_params=query))
            self.assertEqual(len(res), len(outputs))
            self.assertTrue(all(r == ("skip", {}) for r in res), query)

    def test_logs_are_shown_on_open_and_when_the_logs_tab_is_chosen_without_blank_lines(self):
        self.mod.get_last_logs = lambda n: ["first\n", "second\n"]
        self.start()
        logs_box = self.comps("Textbox", "Last 10 log lines")[0]
        demo = self.comps("Blocks")[0]
        loads = [h for h in self.handlers(demo, "load") if h[3] == [logs_box] or h[3] == logs_box]
        self.assertEqual(len(loads), 1)
        self.assertEqual(loads[0][1](), "first\nsecond")
        logs_tab = [c for c in self.comps("Tab") if c.kw.get("id") == "logs"][0]
        (kind, fn, inputs, outputs), = self.handlers(logs_tab, "select")
        self.assertEqual(fn(), "first\nsecond")
        refresh = [c for c in self.comps("Button") if c.args and c.args[0] == "🔄 Refresh logs"][0]
        self.assertEqual(refresh.handlers[0][1](), "first\nsecond")


if __name__ == "__main__":
    unittest.main()
