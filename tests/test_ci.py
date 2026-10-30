import re
import unittest

from tests import stubs

WORKFLOW = stubs.ROOT / ".github" / "workflows" / "tests.yml"
# модуль для импорта : пакет в pip
THIRD_PARTY = {"PIL": "pillow", "yaml": "pyyaml"}


class WorkflowInstallsTestDependenciesTest(unittest.TestCase):
    def imported_third_party(self):
        found = set()
        for p in list((stubs.ROOT / "tests").glob("*.py")) + list((stubs.ROOT / "scripts").glob("*.py")):
            text = p.read_text(encoding="utf-8")
            for mod in THIRD_PARTY:
                if re.search(rf"^\s*(import|from)\s+{mod}\b", text, re.M):
                    # модули, которые тесты заменяют заглушками, в CI не нужны; здесь только прямые импорты
                    found.add(mod)
        return found

    def test_ci_installs_every_third_party_package_imported_without_a_stub(self):
        # torch, cv2, diffusers, gradio, flask заглушаются или не импортируются на уровне модуля в тестах
        text = WORKFLOW.read_text(encoding="utf-8").lower()
        for mod in self.imported_third_party():
            self.assertIn(THIRD_PARTY[mod], text, f"{mod}: нужен pip install {THIRD_PARTY[mod]} в tests.yml")

    def test_notebook_install_cells_include_pyyaml(self):
        import json
        for name in ("SDXL_Vintage_Illustration_FULL_Pro_Turbo_Gallery.ipynb", "GPU_smoke_check.ipynb"):
            nb = json.load(open(stubs.ROOT / "colab" / name, encoding="utf-8"))
            installs = "\n".join("".join(c["source"]) for c in nb["cells"]
                                 if c["cell_type"] == "code" and "pip install" in "".join(c["source"]))
            self.assertIn("pyyaml", installs.lower(), name)


if __name__ == "__main__":
    unittest.main()
