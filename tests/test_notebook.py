import json
import re
import unittest

from tests import stubs

NB = stubs.ROOT / "colab" / "SDXL_Vintage_Illustration_FULL_Pro_Turbo_Gallery.ipynb"
SMOKE_NB = stubs.ROOT / "colab" / "GPU_smoke_check.ipynb"


class NotebookTest(unittest.TestCase):
    def setUp(self):
        self.nb = json.load(open(NB, encoding="utf-8"))

    def test_every_code_cell_is_valid_python(self):
        for i, c in enumerate(self.nb["cells"]):
            if c["cell_type"] != "code":
                continue
            src = "".join(c["source"])
            src = re.sub(r"^(\s*)[!%].*$", r"\1pass", src, flags=re.M)
            try:
                compile(src, f"cell {i}", "exec")
            except SyntaxError as e:
                self.fail(f"cell {i}: {e}")

    def test_scripts_imported_by_notebook_exist(self):
        for c in self.nb["cells"]:
            if c["cell_type"] != "code":
                continue
            for mod in re.findall(r"from scripts\.(\w+) import", "".join(c["source"])):
                self.assertTrue((stubs.ROOT / "scripts" / f"{mod}.py").exists(), mod)

    def test_cells_using_final_prompt_define_it(self):
        # ячейка Upscale падала с NameError, если до неё не запускали другую ячейку
        import ast
        for i, c in enumerate(self.nb["cells"]):
            if c["cell_type"] != "code":
                continue
            src = re.sub(r"^(\s*)[!%].*$", r"\1pass", "".join(c["source"]), flags=re.M)
            names = [(type(n.ctx), n.id) for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Name)]
            if (ast.Load, "final_prompt") in names:
                self.assertIn((ast.Store, "final_prompt"), names, f"cell {i} читает final_prompt, но не задаёт его")

    def test_every_build_prompt_call_passes_style_extra(self):
        # стиль проекта добавляет текст ко всем режимам, не только к Text2Img
        for i, c in enumerate(self.nb["cells"]):
            src = "".join(c["source"]) if c["cell_type"] == "code" else ""
            for call in re.findall(r"build_prompt\((?:[^()]|\([^()]*\))*\)", src):
                if "tone=color_tone" in call:
                    self.assertIn("extra=style_extra", call, f"cell {i}")

    def test_style_extra_defined_before_use_and_project_cell_present(self):
        code = ["".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code"]
        text = "\n".join(code)
        first_def = re.search(r"^style_extra\s*=", text, re.M).start()
        self.assertLess(first_def, text.index("extra=style_extra"))
        self.assertIn("scripts.style_presets", text)

    def test_no_real_politicians_in_example_prompts(self):
        banned = ("trump", "biden", "putin", "obama", "harris")
        text = "\n".join("".join(c["source"]) for c in self.nb["cells"]).lower()
        for name in banned:
            self.assertNotIn(name, text, name)


class SmokeNotebookTest(unittest.TestCase):
    def setUp(self):
        self.nb = json.load(open(SMOKE_NB, encoding="utf-8"))

    def test_code_cells_are_valid_python_and_use_existing_scripts(self):
        for i, c in enumerate(self.nb["cells"]):
            if c["cell_type"] != "code":
                continue
            src = "".join(c["source"])
            compile(re.sub(r"^(\s*)[!%].*$", r"\1pass", src, flags=re.M), f"cell {i}", "exec")
            for mod in re.findall(r"from scripts\.(\w+) import", src):
                self.assertTrue((stubs.ROOT / "scripts" / f"{mod}.py").exists(), mod)

    def test_title_and_first_cell_show_the_same_version_as_the_code(self):
        from scripts import smoke_check
        v = smoke_check.SMOKE_VERSION
        first_md = "".join(self.nb["cells"][0]["source"])
        self.assertEqual(self.nb["cells"][0]["cell_type"], "markdown")
        self.assertIn(f"версия {v}", first_md.splitlines()[0])
        first_code = next("".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code")
        self.assertIn("SMOKE_VERSION", first_code)
        self.assertIn("print(", first_code)

    def test_smoke_modes_exist_in_modes_file(self):
        src = "".join("".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code")
        default = re.search(r'MODES\s*=\s*"([^"]+)"', src).group(1).split(",")
        ids = {m["id"] for m in json.load(open(stubs.ROOT / "presets" / "usa_safari_modes.json", encoding="utf-8"))}
        self.assertTrue(set(default) <= ids)


class ScriptsCompileTest(unittest.TestCase):
    def test_all_scripts_compile(self):
        for p in (stubs.ROOT / "scripts").glob("*.py"):
            compile(p.read_text(encoding="utf-8"), str(p), "exec")


if __name__ == "__main__":
    unittest.main()
