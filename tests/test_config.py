import re
import unittest

from tests import stubs

stubs.install()
from scripts.config import VARIANT_MODELS  # noqa: E402

VARIANTS = ("SDXL", "SDXL_TURBO", "SD15")
HF_ID = re.compile(r"^[\w.-]+/[\w.-]+$")


class VariantModelsTest(unittest.TestCase):
    def test_every_variant_has_basic_tasks(self):
        for v in VARIANTS:
            for key in ("txt2img", "img2img", "controlnet", "upscale", "inpaint"):
                self.assertIn(key, VARIANT_MODELS[v], f"{v}.{key}")

    def test_all_model_ids_look_like_hf_repo_ids(self):
        for v in VARIANTS:
            for key, val in VARIANT_MODELS[v].items():
                self.assertRegex(val, HF_ID, f"{v}.{key}")

    def test_turbo_has_separate_base_for_controlnet(self):
        # turbo не годится как база ControlNet: нужен базовый SDXL
        self.assertEqual(VARIANT_MODELS["SDXL_TURBO"]["controlnet_model"],
                         VARIANT_MODELS["SDXL"]["txt2img"])


class ControlnetTypesTest(unittest.TestCase):
    """Новый код: usa_safari.py выбирает ControlNet по ключу controlnet_<тип>."""

    def test_canny_and_openpose_per_variant(self):
        for v in VARIANTS:
            for key in ("controlnet_canny", "controlnet_openpose"):
                self.assertIn(key, VARIANT_MODELS[v], f"{v}.{key}")

    def test_canny_matches_legacy_controlnet_key(self):
        for v in VARIANTS:
            self.assertEqual(VARIANT_MODELS[v]["controlnet_canny"], VARIANT_MODELS[v]["controlnet"])


if __name__ == "__main__":
    unittest.main()
