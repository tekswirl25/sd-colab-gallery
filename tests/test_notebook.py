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

    # ячейка: (часть заголовка, вызов, сколько строк кода допустимо)
    THIN = (
        ("📥 Репозиторий", "git clone", 9),
        ("🚀 Старт", "setup_all", 12),
        ("🎨 Стиль и проект", "apply_style", 10),
        ("USA Safari — Генератор", "show_generator", 8),
        ("USA Safari — Drive Reference Setup", "setup_drive_reference", 8),
        ("🖼 Text2Img", "run_text2img", 9),
        ("Upload image (Img2Img)", "show_upload", 8),
        ("Img2Img — unified", "run_img2img", 9),
        ("Upload image (ControlNet)", "show_upload", 8),
        ("ControlNet — unified", "run_controlnet", 10),
        ("Upload image (Inpainting)", "show_upload", 8),
        ("Upload mask (Inpainting)", "show_upload", 8),
        ("Inpainting — replace", "run_inpaint", 9),
        ("Upscale x4", "run_upscale", 8),
    )

    def first_lines(self):
        return ["".join(c["source"]).splitlines()[0] for c in self.nb["cells"] if c["cell_type"] == "code"]

    def test_cells_are_fields_and_one_call_with_code_in_project_scripts(self):
        # правило owner: в ноутбуке только поля и вызов, весь код в scripts/
        for title, call, limit in self.THIN:
            cell = next((("".join(c["source"])) for c in self.nb["cells"]
                         if c["cell_type"] == "code" and title in "".join(c["source"]).splitlines()[0]), None)
            self.assertIsNotNone(cell, f"нет ячейки {title}")
            self.assertIn(call, cell, title)
            code_lines = [l for l in cell.splitlines() if l.strip() and not l.strip().startswith("#")]
            self.assertLessEqual(len(code_lines), limit, f"{title}: {len(code_lines)} строк кода, можно {limit}")

    def test_no_code_cell_is_left_with_a_lot_of_code(self):
        for i, c in enumerate(self.nb["cells"]):
            if c["cell_type"] != "code":
                continue
            lines = [l for l in "".join(c["source"]).splitlines() if l.strip() and not l.strip().startswith("#")]
            self.assertLessEqual(len(lines), 12, f"cell {i}: {len(lines)} строк кода")

    def test_start_cells_come_first_then_style_then_modes(self):
        order = ("📥 Репозиторий", "🚀 Старт", "🎨 Стиль и проект", "Text2Img", "Img2Img — unified", "Upscale")
        titles = self.first_lines()
        pos = [next(i for i, t in enumerate(titles) if k in t) for k in order]
        self.assertEqual(pos, sorted(pos))

    def test_old_service_cells_are_gone_because_start_does_it_all(self):
        text = "\n".join(self.first_lines())
        for gone in ("Mount Google Drive", "Config Init", "Install dependencies", "Imports & utils", "Model loaders",
                     "Style base"):
            self.assertNotIn(gone, text, gone)

    def test_title_shows_notebook_version(self):
        from scripts import notebook_version
        v = notebook_version.NOTEBOOK_VERSION
        self.assertRegex(v, r"^\d{14}$")
        self.assertEqual(self.nb["cells"][0]["cell_type"], "markdown")
        self.assertIn(f"версия {v}", "".join(self.nb["cells"][0]["source"]).splitlines()[0])

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

    def test_cache_check_cell_sits_between_drive_mount_and_the_run(self):
        code = ["".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code"]
        idx = {k: next(i for i, s in enumerate(code) if k in s)
               for k in ("drive.mount", "hf_cache_check", "run_smoke(")}
        self.assertLess(idx["drive.mount"], idx["hf_cache_check"])
        self.assertLess(idx["hf_cache_check"], idx["run_smoke("])
        cell = code[idx["hf_cache_check"]]
        self.assertIn("DELETE_BROKEN = False", cell)  # по умолчанию ничего не удаляется

    def test_diagnose_cell_follows_the_run_and_does_not_delete(self):
        code = ["".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code"]
        run = next(i for i, s in enumerate(code) if "run_smoke(" in s)
        diag = next(i for i, s in enumerate(code) if "hf_diagnose" in s)
        self.assertLess(run, diag)
        self.assertNotIn("remove_models", code[diag])
        self.assertNotIn("rmtree", code[diag])

    def test_smoke_modes_exist_in_modes_file(self):
        src = "".join("".join(c["source"]) for c in self.nb["cells"] if c["cell_type"] == "code")
        default = re.search(r'MODES\s*=\s*"([^"]+)"', src).group(1).split(",")
        ids = {m["id"] for m in json.load(open(stubs.ROOT / "presets" / "usa_safari_modes.json", encoding="utf-8"))}
        self.assertTrue(set(default) <= ids)


class FormViewTest(unittest.TestCase):
    """Код ячеек с #@title скрыт: видны только поля и кнопка запуска (cellView: form)."""

    def test_every_titled_code_cell_is_in_form_view_in_both_notebooks(self):
        for path in (NB, SMOKE_NB):
            nb = json.load(open(path, encoding="utf-8"))
            for i, c in enumerate(nb["cells"]):
                if c["cell_type"] != "code":
                    continue
                first = "".join(c["source"]).lstrip().splitlines()[0]
                if "@title" in first:
                    self.assertEqual(c.get("metadata", {}).get("cellView"), "form", f"{path.name} cell {i}: {first}")


class HfCacheLocationTest(unittest.TestCase):
    """Google Drive не поддерживает символьные ссылки, на которых держится кеш Hugging Face."""

    def test_default_hf_cache_is_not_on_drive_in_any_notebook(self):
        for nb_path in (NB, SMOKE_NB):
            nb = json.load(open(nb_path, encoding="utf-8"))
            text = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
            m = re.search(r'^HF_CACHE_DIR\s*=\s*"([^"]+)"', text, re.M)
            self.assertIsNotNone(m, nb_path.name)
            self.assertFalse(m.group(1).startswith("/content/drive"), f"{nb_path.name}: {m.group(1)}")


class ScriptsCompileTest(unittest.TestCase):
    def test_all_scripts_compile(self):
        for p in (stubs.ROOT / "scripts").glob("*.py"):
            compile(p.read_text(encoding="utf-8"), str(p), "exec")


if __name__ == "__main__":
    unittest.main()
