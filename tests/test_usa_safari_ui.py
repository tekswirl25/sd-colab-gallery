import contextlib
import io
import os
import sys
import tempfile
import types
import unittest

from tests import stubs

stubs.install()


# ---- заглушка ipywidgets: хранит свойства, вызывает observe при смене value, on_click по команде ----
class Layout:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Widget:
    def __init__(self, *args, **kw):
        object.__setattr__(self, "_obs", [])
        object.__setattr__(self, "_click", [])
        if args:  # VBox/HBox(children), HTML(value)
            self.__dict__["children"] = args[0]
            kw.setdefault("value", args[0])
        self.__dict__.update(kw)
        self.__dict__.setdefault("layout", Layout())
        defaults = {"Text": "", "Textarea": "", "Checkbox": False, "FileUpload": (), "Button": None}
        self.__dict__.setdefault("value", defaults.get(type(self).__name__, kw.get("value")))  # как в ipywidgets

    def __setattr__(self, name, val):
        old = self.__dict__.get(name)
        self.__dict__[name] = val
        if name == "value" and old != val:
            for fn in self._obs:
                fn({"new": val, "old": old, "name": "value"})

    def observe(self, fn, names=None):
        self._obs.append(fn)

    def on_click(self, fn):
        self._click.append(fn)

    def click(self):
        for fn in self._click:
            fn(self)


class Output(Widget):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        object.__setattr__(self, "buf", io.StringIO())

    def __enter__(self):
        self._ctx = contextlib.redirect_stdout(self.buf)
        self._ctx.__enter__()
        return self

    def __exit__(self, *a):
        self._ctx.__exit__(*a)

    @property
    def text(self):
        return self.buf.getvalue()


def fake_widgets():
    m = types.ModuleType("ipywidgets")
    m.Layout = Layout
    for name in ("Textarea", "Button", "Checkbox", "FileUpload", "Text", "HTML", "VBox", "HBox"):
        setattr(m, name, type(name, (Widget,), {}))

    class Dropdown(Widget):
        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            if self.__dict__.get("value") is None and kw.get("options"):
                self.__dict__["value"] = kw["options"][0][1]  # как в ipywidgets: первый пункт

    m.Dropdown = Dropdown
    m.Output = Output
    return m


def fake_display():
    shown = []
    return types.SimpleNamespace(display=lambda *a, **k: shown.extend(a), clear_output=lambda *a, **k: None,
                                 shown=shown)


class UiBase(unittest.TestCase):
    def setUp(self):
        for k in ("scripts.loaders", "scripts.utils", "scripts.usa_safari", "scripts.usa_safari_ui"):
            sys.modules.pop(k, None)
        self._cwd = os.getcwd()
        os.chdir(stubs.ROOT)  # presets/ читается по относительному пути
        from scripts import usa_safari_ui
        self.ui = usa_safari_ui
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        os.chdir(self._cwd)
        self.tmp.cleanup()


class PureHelpersTest(UiBase):
    def modes(self):
        from scripts import usa_safari
        return usa_safari.list_modes()

    def test_mode_options_come_from_modes_file(self):
        opts = self.ui.mode_options(self.modes())
        self.assertEqual([v for _, v in opts], [m["id"] for m in self.modes()])
        self.assertEqual(opts[0][0], "1. Editorial VO — основные иллюстрации выпуска")

    def test_uploads_needed_by_mode_type(self):
        by = {m["id"]: m for m in self.modes()}
        self.assertEqual(self.ui.uploads_needed(by["editorial-vo"]), (False, False))
        self.assertEqual(self.ui.uploads_needed(by["news-screenshot"]), (True, False))
        self.assertEqual(self.ui.uploads_needed(by["inpaint-face"]), (True, True))

    def test_brief_to_fields_full(self):
        text = ("[Inpaint Anatomy]\nСцена: сенатор у трибуны\nПерсонаж: да\nЕсли да: силуэт\n"
                "Исходник: есть (тип: screenshot)\nIP-Adapter: да (ref: Official.jpg)")
        f = self.ui.brief_to_fields(text, self.modes(), ip_ref_dir="/drive/chars")
        self.assertEqual(f["mode_id"], "inpaint-anatomy")
        self.assertEqual(f["scene"], "сенатор у трибуны, силуэт")
        self.assertTrue(f["with_character"])
        self.assertTrue(f["use_ip"])
        self.assertEqual(f["ip_path"], "/drive/chars/Official.jpg")

    def test_brief_to_fields_defaults_and_unknown_mode(self):
        f = self.ui.brief_to_fields("Сцена: улица\nПерсонаж: нет", self.modes(), ip_ref_dir="/x")
        self.assertEqual((f["mode_id"], f["scene"], f["with_character"], f["use_ip"], f["ip_path"]),
                         ("editorial-vo", "улица", False, False, ""))

    def test_describe_mode_lists_prompts_and_params(self):
        mode = next(m for m in self.modes() if m["id"] == "inpaint-anatomy")
        text = self.ui.describe_mode(mode)
        self.assertIn(mode["label"], text)
        self.assertIn(mode["positive"], text)
        self.assertIn("Steps: 30", text)

    def test_save_uploaded_handles_tuple_dict_and_empty(self):
        d = self.tmp.name
        tup = types.SimpleNamespace(value=({"name": "a.png", "content": b"AA"},))
        old = types.SimpleNamespace(value={"b.png": {"content": b"BB"}})
        none = types.SimpleNamespace(value=())
        p1 = self.ui.save_uploaded(tup, "src", d)
        p2 = self.ui.save_uploaded(old, "mask", d)
        with open(p1, "rb") as f1, open(p2, "rb") as f2:
            self.assertEqual((f1.read(), f2.read()), (b"AA", b"BB"))
        self.assertTrue(os.path.basename(p1).startswith("usa_safari_src_"))
        self.assertIsNone(self.ui.save_uploaded(none, "src", d))


class WidgetsTest(UiBase):
    def build(self, runner=None):
        calls = []

        def default_runner(mode, positive, negative, config, output_dir, **kw):
            calls.append((mode, positive, negative, config, output_dir, kw))
            return os.path.join(output_dir, "x.png")

        self.calls = calls
        self.disp = fake_display()
        return self.ui.build_ui(
            config={"OUTPUT_DIR": self.tmp.name, "MODEL_VARIANT": "SD15"}, ip_ref_dir="/drive/chars",
            upload_dir=self.tmp.name, widgets=fake_widgets(), ipy_display=self.disp,
            runner=runner or default_runner)

    def test_ui_is_shown_and_has_main_controls(self):
        ui = self.build()
        self.assertTrue(self.disp.shown)
        self.assertEqual(ui.mode_dd.options[0][1], "editorial-vo")
        self.assertEqual(ui.gen_btn.description, "⚡ GENERATE")

    def test_upload_boxes_follow_the_mode(self):
        ui = self.build()
        self.assertEqual((ui.src_box.layout.display, ui.mask_box.layout.display), ("none", "none"))
        ui.mode_dd.value = "news-screenshot"
        self.assertEqual((ui.src_box.layout.display, ui.mask_box.layout.display), ("", "none"))
        ui.mode_dd.value = "inpaint-face"
        self.assertEqual((ui.src_box.layout.display, ui.mask_box.layout.display), ("", ""))
        ui.mode_dd.value = "editorial-vo"
        self.assertEqual((ui.src_box.layout.display, ui.mask_box.layout.display), ("none", "none"))

    def test_parse_button_fills_fields(self):
        ui = self.build()
        ui.brief_ta.value = "[News Screenshot]\nСцена: заголовок\nПерсонаж: да\nIP-Adapter: да (ref: A.jpg)"
        ui.parse_btn.click()
        self.assertEqual(ui.mode_dd.value, "news-screenshot")
        self.assertEqual(ui.scene_ta.value, "заголовок")
        self.assertTrue(ui.with_char_cb.value)
        self.assertTrue(ui.ip_cb.value)
        self.assertEqual(ui.ip_path_w.value, "/drive/chars/A.jpg")
        self.assertIn("Режим: news-screenshot", ui.parse_out.text)

    def test_parse_with_empty_brief_asks_for_text(self):
        ui = self.build()
        ui.parse_btn.click()
        self.assertIn("Введи текст брифа", ui.parse_out.text)

    def test_show_params_prints_mode_description(self):
        ui = self.build()
        ui.show_params_cb.value = True
        self.assertIn("1. Editorial VO", ui.params_out.text)

    def test_generate_calls_runner_with_prompts_and_reenables_button(self):
        ui = self.build()
        ui.scene_ta.value = "a senator at a podium"
        ui.with_char_cb.value = True
        ui.gen_btn.click()
        (mode, positive, negative, config, out_dir, kw), = self.calls
        self.assertEqual(mode["id"], "editorial-vo")
        self.assertIn("a senator at a podium", positive)
        self.assertIn(mode["anatomy_addon"], positive)
        self.assertEqual(out_dir, self.tmp.name)
        self.assertEqual((kw["src_path"], kw["mask_path"], kw["ip_ref_path"]), (None, None, None))
        self.assertFalse(ui.gen_btn.disabled)
        self.assertIn("Готово", ui.status_out.text)

    def test_generate_passes_typed_paths_for_inpaint(self):
        ui = self.build()
        ui.mode_dd.value = "inpaint-anatomy"
        ui.src_path_w.value = "/content/s.png"
        ui.mask_path_w.value = "/content/m.png"
        ui.gen_btn.click()
        kw = self.calls[0][5]
        self.assertEqual((kw["src_path"], kw["mask_path"]), ("/content/s.png", "/content/m.png"))

    def test_ip_reference_used_only_when_checkbox_on(self):
        ui = self.build()
        ui.ip_path_w.value = "/drive/chars/A.jpg"
        ui.gen_btn.click()
        self.assertIsNone(self.calls[0][5]["ip_ref_path"])
        ui.ip_cb.value = True
        ui.gen_btn.click()
        self.assertEqual(self.calls[1][5]["ip_ref_path"], "/drive/chars/A.jpg")

    def test_runner_error_is_shown_and_button_reenabled(self):
        def boom(*a, **k):
            raise ValueError("Для inpaint нужна маска")
        ui = self.build(runner=boom)
        ui.gen_btn.click()
        self.assertIn("Ошибка: Для inpaint нужна маска", ui.status_out.text)
        self.assertFalse(ui.gen_btn.disabled)


if __name__ == "__main__":
    unittest.main()
