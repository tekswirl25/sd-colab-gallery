import importlib
import sys
import types
import unittest

from tests import stubs

stubs.install()


class Recorder:
    """Заменяет класс diffusers: запоминает аргументы from_pretrained."""

    calls = []

    @classmethod
    def from_pretrained(cls, model_id, **kw):
        cls.calls.append((model_id, kw))
        obj = cls()
        return obj

    def to(self, device):
        return self

    def enable_xformers_memory_efficient_attention(self):
        pass


def load_loaders():
    diffusers = types.ModuleType("diffusers")
    for name in ("AutoPipelineForText2Image", "AutoPipelineForImage2Image", "AutoPipelineForInpainting",
                 "StableDiffusionXLControlNetPipeline", "StableDiffusionControlNetPipeline",
                 "StableDiffusionUpscalePipeline", "ControlNetModel"):
        setattr(diffusers, name, type(name, (Recorder,), {"calls": []}))
    sys.modules["diffusers"] = diffusers
    utils = types.ModuleType("scripts.utils")
    utils.free_memory = lambda: None
    sys.modules["scripts.utils"] = utils
    sys.modules.pop("scripts.loaders", None)
    loaders = importlib.import_module("scripts.loaders")  # заново, а не из атрибута пакета
    return loaders, diffusers


class InpaintSafetensorsTest(unittest.TestCase):
    def tearDown(self):
        for k in ("diffusers", "scripts.utils", "scripts.loaders"):
            sys.modules.pop(k, None)

    def test_fp16_inpaint_loads_only_safe_fp16_weights(self):
        # у inpaint-репозитория есть только fp16 safetensors; pickle .bin загружать нельзя (контракт)
        loaders, diffusers = load_loaders()
        loaders.reset_pipes()
        loaders.get_inpaint_pipe("runwayml/stable-diffusion-inpainting", "cuda", sys.modules["torch"].float16)
        (model_id, kw), = diffusers.AutoPipelineForInpainting.calls
        self.assertEqual(model_id, "runwayml/stable-diffusion-inpainting")
        self.assertIs(kw["use_safetensors"], True)
        self.assertEqual(kw["variant"], "fp16")

    def test_float32_inpaint_still_demands_safetensors_and_has_no_variant(self):
        loaders, diffusers = load_loaders()
        loaders.reset_pipes()
        loaders.get_inpaint_pipe("runwayml/stable-diffusion-inpainting", "cpu", sys.modules["torch"].float32)
        (_, kw), = diffusers.AutoPipelineForInpainting.calls
        self.assertIs(kw["use_safetensors"], True)
        self.assertNotIn("variant", kw)


if __name__ == "__main__":
    unittest.main()
