import json
import re
import unittest

from tests import stubs

NB = stubs.ROOT / "colab" / "SDXL_Vintage_Illustration_FULL_Pro_Turbo_Gallery.ipynb"


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

    def test_no_real_politicians_in_example_prompts(self):
        banned = ("trump", "biden", "putin", "obama", "harris")
        text = "\n".join("".join(c["source"]) for c in self.nb["cells"]).lower()
        for name in banned:
            self.assertNotIn(name, text, name)


class ScriptsCompileTest(unittest.TestCase):
    def test_all_scripts_compile(self):
        for p in (stubs.ROOT / "scripts").glob("*.py"):
            compile(p.read_text(encoding="utf-8"), str(p), "exec")


if __name__ == "__main__":
    unittest.main()
