import os
import unittest
from pathlib import Path

from tests import stubs

stubs.install()
from scripts import prompt_builder  # noqa: E402


class BuildPromptTest(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(stubs.ROOT)  # PRESETS_DIR относительный, как в Colab

    def tearDown(self):
        os.chdir(self._cwd)

    def test_plain_text_without_style(self):
        self.assertEqual(prompt_builder.build_prompt("a cat"), "a cat")

    def test_missing_style_is_ignored(self):
        self.assertEqual(prompt_builder.build_prompt("a cat", style="no-such-style"), "a cat")


class FullStyleTest(unittest.TestCase):
    """Новый код: полные пресеты USA Safari."""

    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(stubs.ROOT)

    def tearDown(self):
        os.chdir(self._cwd)

    def test_list_and_get(self):
        names = prompt_builder.list_full_styles()
        self.assertTrue(names)
        for n in names:
            p = prompt_builder.get_full_style(n)
            self.assertEqual(p["name"], n)
            for k in ("positive", "negative", "width", "height", "steps", "cfg"):
                self.assertIn(k, p, f"{n}.{k}")

    def test_unknown_gives_none(self):
        self.assertIsNone(prompt_builder.get_full_style("nope"))


if __name__ == "__main__":
    unittest.main()
