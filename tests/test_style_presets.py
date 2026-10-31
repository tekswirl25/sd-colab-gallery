import json
import os
import tempfile
import unittest

import yaml
from PIL import Image

from tests import stubs

stubs.install()
from scripts import style_presets  # noqa: E402


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)


class TreeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.tmp.name, "prompts")
        self.presets = os.path.join(self.tmp.name, "presets")
        os.makedirs(self.presets)
        json.dump([{"name": "illustration", "prompt": "hand-drawn, ink"}],
                  open(os.path.join(self.presets, "styles.json"), "w"))
        json.dump([{"name": "vintage", "prompt": "faded palette"}],
                  open(os.path.join(self.presets, "color_tones.json"), "w"))
        self.drive_out = os.path.join(self.tmp.name, "drive", "film", "out")  # только во временной папке
        write(f"{self.root}/film/project.yaml",
              {"name": "film", "default_style": "ink", "drive_output_dir": self.drive_out})
        write(f"{self.root}/film/styles/ink.yaml",
              {"label": "Ink", "base_style": "illustration", "color_tone": "vintage",
               "positive": "1940s, sepia", "negative": "anime",
               "params": {"steps": 30, "cfg": 6.5, "width": 1024, "height": 1024}})
        write(f"{self.root}/film/characters/dora.yaml", {"prompt": "thin girl, bob haircut", "seeds": [1001, 1002]})
        write(f"{self.root}/_shared/styles/plain.yaml", {"label": "Plain", "positive": "plain", "negative": "text"})
        write(f"{self.root}/other/project.yaml", {"name": "other", "default_style": "plain"})

    def tearDown(self):
        self.tmp.cleanup()

    def kw(self):
        return dict(root=self.root)


class ListingTest(TreeCase):
    def test_projects_skip_shared_and_dirs_without_project_file(self):
        os.makedirs(f"{self.root}/notaproject")
        self.assertEqual(style_presets.list_projects(self.root), ["film", "other"])

    def test_styles_are_project_plus_shared(self):
        self.assertEqual(style_presets.list_styles("film", self.root), ["ink", "plain"])
        self.assertEqual(style_presets.list_styles("other", self.root), ["plain"])

    def test_project_style_overrides_shared_with_same_name(self):
        write(f"{self.root}/film/styles/plain.yaml", {"positive": "film plain"})
        self.assertEqual(style_presets.load_style("film", "plain", self.root)["positive"], "film plain")
        self.assertEqual(style_presets.load_style("other", "plain", self.root)["positive"], "plain")

    def test_characters(self):
        self.assertEqual(style_presets.list_characters("film", self.root), ["dora"])
        self.assertEqual(style_presets.load_character("film", "dora", self.root)["seeds"], [1001, 1002])


class ExtendsTest(TreeCase):
    def test_child_overrides_scalars_and_merges_params(self):
        write(f"{self.root}/film/styles/ink_wide.yaml",
              {"extends": "ink", "positive": "wide", "params": {"width": 1344, "height": 768}})
        s = style_presets.load_style("film", "ink_wide", self.root)
        self.assertEqual(s["positive"], "wide")                 # заменено
        self.assertEqual(s["negative"], "anime")                # унаследовано
        self.assertEqual(s["params"], {"steps": 30, "cfg": 6.5, "width": 1344, "height": 768})
        self.assertNotIn("extends", s)

    def test_extends_shared_style(self):
        write(f"{self.root}/film/styles/mine.yaml", {"extends": "plain", "negative": "photo"})
        s = style_presets.load_style("film", "mine", self.root)
        self.assertEqual((s["positive"], s["negative"]), ("plain", "photo"))

    def test_cycle_is_detected(self):
        write(f"{self.root}/film/styles/a.yaml", {"extends": "b"})
        write(f"{self.root}/film/styles/b.yaml", {"extends": "a"})
        with self.assertRaisesRegex(ValueError, "цикл"):
            style_presets.load_style("film", "a", self.root)

    def test_unknown_parent_names_the_style(self):
        write(f"{self.root}/film/styles/a.yaml", {"extends": "ghost"})
        with self.assertRaisesRegex(ValueError, "ghost"):
            style_presets.load_style("film", "a", self.root)


class ErrorsTest(TreeCase):
    def test_unknown_style_lists_available(self):
        with self.assertRaisesRegex(ValueError, "ink, plain"):
            style_presets.load_style("film", "nope", self.root)

    def test_unknown_project_lists_available(self):
        with self.assertRaisesRegex(ValueError, "film, other"):
            style_presets.load_project("nope", self.root)


class ComposeTest(TreeCase):
    def compose(self, **kw):
        return style_presets.compose("film", kw.pop("style", "ink"), "a girl at a well",
                                     root=self.root, presets_dir=self.presets, **kw)

    def test_order_scene_style_tone_character_addition(self):
        r = self.compose(character="dora")
        self.assertEqual(r["positive"],
                         "a girl at a well, hand-drawn, ink, faded palette, thin girl, bob haircut, 1940s, sepia")
        self.assertEqual(r["negative"], "anime")

    def test_without_character(self):
        self.assertEqual(self.compose()["positive"],
                         "a girl at a well, hand-drawn, ink, faded palette, 1940s, sepia")

    def test_style_without_base_and_tone(self):
        self.assertEqual(self.compose(style="plain")["positive"], "a girl at a well, plain")

    def test_params_and_output_dir_come_from_style_and_project(self):
        r = self.compose()
        self.assertEqual(r["params"], {"steps": 30, "cfg": 6.5, "width": 1024, "height": 1024})
        self.assertEqual(r["drive_output_dir"], self.drive_out)

    def test_default_style_used_when_none_given(self):
        r = style_presets.compose("film", None, "x", root=self.root, presets_dir=self.presets)
        self.assertEqual(r["style"], "ink")

    def test_project_without_drive_dir_gives_none(self):
        r = style_presets.compose("other", None, "x", root=self.root, presets_dir=self.presets)
        self.assertIsNone(r["drive_output_dir"])

    def test_unknown_base_style_name_is_an_error(self):
        write(f"{self.root}/film/styles/bad.yaml", {"base_style": "no-such"})
        with self.assertRaisesRegex(ValueError, "no-such"):
            self.compose(style="bad")


class ResolveTest(TreeCase):
    def test_resolve_gives_names_extra_negative_params(self):
        r = style_presets.resolve("film", "ink", "dora", root=self.root, presets_dir=self.presets)
        self.assertEqual((r["base_style"], r["color_tone"]), ("illustration", "vintage"))
        self.assertEqual(r["extra"], "thin girl, bob haircut, 1940s, sepia")
        self.assertEqual(r["negative"], "anime")
        self.assertEqual(r["params"]["width"], 1024)

    def test_resolve_without_character_extra_is_style_positive(self):
        r = style_presets.resolve("film", "ink", root=self.root, presets_dir=self.presets)
        self.assertEqual(r["extra"], "1940s, sepia")

    def test_resolve_style_without_names_gives_none(self):
        r = style_presets.resolve("other", "plain", root=self.root, presets_dir=self.presets)
        self.assertIsNone(r["base_style"])
        self.assertIsNone(r["color_tone"])


class ApplyStyleTest(TreeCase):
    def apply(self, **kw):
        cfg = {"OUTPUT_DIR": "/content/outputs"}
        args = dict(project="film", style=None, character=None, save_to_drive=True, config=cfg,
                    base_style="photoreal", color_tone="warm", negative="", root=self.root,
                    presets_dir=self.presets)
        args.update(kw)
        return style_presets.apply_style(**args), cfg

    def test_returns_values_the_notebook_needs(self):
        r, _ = self.apply(character="dora", style="")
        self.assertEqual((r["base_style"], r["color_tone"]), ("illustration", "vintage"))
        self.assertEqual(r["negative"], "anime")
        self.assertEqual(r["style_extra"], "thin girl, bob haircut, 1940s, sepia")
        self.assertEqual(r["style_suffix"], "hand-drawn, ink, faded palette, thin girl, bob haircut, 1940s, sepia")
        self.assertEqual(r["active_preset"]["width"], 1024)

    def test_style_without_names_keeps_current_base_and_tone(self):
        r, _ = self.apply(style="plain")
        self.assertEqual((r["base_style"], r["color_tone"]), ("photoreal", "warm"))

    def test_output_dir_switches_to_drive_folder_and_is_created(self):
        with tempfile.TemporaryDirectory() as d:
            write(f"{self.root}/film/project.yaml", {"name": "film", "default_style": "ink", "drive_output_dir": f"{d}/out"})
            r, cfg = self.apply()
            self.assertEqual(cfg["OUTPUT_DIR"], f"{d}/out")
            self.assertTrue(os.path.isdir(f"{d}/out"))

    def test_save_to_drive_off_keeps_output_dir(self):
        r, cfg = self.apply(save_to_drive=False)
        self.assertEqual(cfg["OUTPUT_DIR"], "/content/outputs")

    def test_unknown_style_error_lists_available(self):
        with self.assertRaisesRegex(ValueError, "ink, plain"):
            self.apply(style="nope")

    def test_without_project_only_base_style_and_tone_are_used(self):
        r, cfg = self.apply(project="", negative="blurry", base_style="illustration", color_tone="vintage")
        self.assertEqual((r["base_style"], r["color_tone"], r["negative"]), ("illustration", "vintage", "blurry"))
        self.assertEqual((r["style_extra"], r["style_suffix"]), ("", "hand-drawn, ink, faded palette"))
        self.assertIsNone(r["active_preset"])
        self.assertEqual(cfg["OUTPUT_DIR"], "/content/outputs")


class RepositoryTreeTest(unittest.TestCase):
    """Настоящее дерево prompts/ репозитория должно быть целым."""

    def test_every_project_and_style_composes(self):
        root, presets = str(stubs.ROOT / "prompts"), str(stubs.ROOT / "presets")
        projects = style_presets.list_projects(root)
        self.assertTrue(projects)
        for p in projects:
            for s in style_presets.list_styles(p, root):
                r = style_presets.compose(p, s, "test scene", root=root, presets_dir=presets)
                self.assertTrue(r["positive"], f"{p}/{s}")
            for c in style_presets.list_characters(p, root):
                style_presets.compose(p, None, "x", character=c, root=root, presets_dir=presets)


class AlphaSaveTest(unittest.TestCase):
    def test_png_keeps_transparency(self):
        import sys
        import types
        utils = types.ModuleType("scripts.utils_real")
        # настоящий utils тянет cv2; проверяем только функцию сохранения
        src = (stubs.ROOT / "scripts" / "utils.py").read_text(encoding="utf-8")
        start = src.index("def save_image_and_meta")
        end = src.index("def free_memory")
        ns = {"os": os, "json": json, "time": __import__("time"), "Path": __import__("pathlib").Path}
        exec(src[start:end], ns)
        with tempfile.TemporaryDirectory() as d:
            im = Image.new("RGBA", (32, 32), (255, 0, 0, 0))
            path, _ = ns["save_image_and_meta"](im, "t", {}, d, mode="text2img")
            self.assertEqual(Image.open(path).mode, "RGBA")
            self.assertEqual(Image.open(path).getpixel((1, 1))[3], 0)


if __name__ == "__main__":
    unittest.main()
