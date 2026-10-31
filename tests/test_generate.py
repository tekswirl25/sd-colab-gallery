import os
import sys
import tempfile
import types
import unittest

from PIL import Image

from tests import stubs

stubs.install()
from scripts import generate  # noqa: E402


class FakePipe:
    def __init__(self):
        self.calls = []

    def __call__(self, **kw):
        self.calls.append(kw)
        return types.SimpleNamespace(images=[Image.new("RGB", (16, 16), "white")])


class Text2ImgTest(unittest.TestCase):
    DEFAULTS = {"txt2img_steps": 30, "txt2img_cfg": 6.5, "img_size": (768, 512)}  # (высота, ширина)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pipe = FakePipe()
        self.pipe_args = []
        self.saved = []
        self.config = {"MODEL_VARIANT": "SD15", "DEVICE": "cpu", "DTYPE": "float32", "OUTPUT_DIR": self.tmp.name}

    def tearDown(self):
        self.tmp.cleanup()

    def run_t2i(self, **kw):
        def get_pipe(model_id, device, dtype):
            self.pipe_args.append((model_id, device, dtype))
            return self.pipe

        def save(im, prefix, meta, output_dir, mode):
            self.saved.append((prefix, meta, output_dir, mode))
            return os.path.join(output_dir, f"{prefix}_{len(self.saved)}.png"), "x.json"

        args = dict(config=self.config, defaults=self.DEFAULTS, user_prompt="a cat", seed=100, n=1,
                    style_suffix="hand-drawn", negative="", active_preset=None,
                    get_pipe=get_pipe, save=save)
        args.update(kw)
        return generate.run_text2img(**args)

    def test_prompt_joins_style_suffix_and_empty_suffix_is_skipped(self):
        self.run_t2i()
        self.assertEqual(self.pipe.calls[0]["prompt"], "a cat, hand-drawn")
        self.run_t2i(style_suffix="")
        self.assertEqual(self.pipe.calls[1]["prompt"], "a cat")

    def test_model_id_comes_from_variant(self):
        self.run_t2i()
        self.assertEqual(self.pipe_args[0][0], "stable-diffusion-v1-5/stable-diffusion-v1-5")
        self.config["MODEL_VARIANT"] = "SDXL_TURBO"
        self.run_t2i()
        self.assertEqual(self.pipe_args[1][0], "stabilityai/sdxl-turbo")

    def test_defaults_used_without_preset(self):
        self.run_t2i()
        kw = self.pipe.calls[0]
        self.assertEqual((kw["num_inference_steps"], kw["guidance_scale"], kw["height"], kw["width"]),
                         (30, 6.5, 768, 512))

    def test_preset_overrides_defaults_and_partial_preset_falls_back(self):
        self.run_t2i(active_preset={"steps": 20, "cfg": 5.0, "width": 1024, "height": 640})
        kw = self.pipe.calls[0]
        self.assertEqual((kw["num_inference_steps"], kw["guidance_scale"], kw["height"], kw["width"]),
                         (20, 5.0, 640, 1024))
        self.run_t2i(active_preset={"steps": 12})
        kw = self.pipe.calls[1]
        self.assertEqual((kw["num_inference_steps"], kw["guidance_scale"], kw["height"], kw["width"]),
                         (12, 6.5, 768, 512))

    def test_empty_preset_means_defaults(self):
        self.run_t2i(active_preset={})
        self.assertEqual(self.pipe.calls[0]["num_inference_steps"], 30)

    def test_negative_is_none_when_empty(self):
        self.run_t2i(negative="")
        self.assertIsNone(self.pipe.calls[0]["negative_prompt"])
        self.run_t2i(negative="anime")
        self.assertEqual(self.pipe.calls[1]["negative_prompt"], "anime")

    def test_n_images_get_consecutive_seeds_and_are_saved_to_text2img(self):
        saved = self.run_t2i(seed=100, n=3)
        self.assertEqual(len(saved), 3)
        self.assertEqual([m["seed"] for _, m, _, _ in self.saved], [100, 101, 102])
        self.assertEqual([c["generator"].seed for c in self.pipe.calls], [100, 101, 102])
        prefix, meta, out_dir, mode = self.saved[0]
        self.assertEqual((prefix, mode, out_dir), ("text2img", "text2img", self.tmp.name))
        self.assertEqual(meta["prompt"], "a cat, hand-drawn")
        self.assertEqual(meta["size"], [768, 512])
        self.assertEqual(meta["mode"], "text2img")

    def test_float_n_from_notebook_form_is_accepted(self):
        self.assertEqual(len(self.run_t2i(n=2.0)), 2)

    def test_non_positive_seed_means_random_seed(self):
        self.run_t2i(seed=0)
        self.assertEqual(self.saved[0][1]["seed"], 123456789)  # torch.seed() заглушки

    def test_returns_saved_paths(self):
        paths = self.run_t2i(n=2)
        self.assertEqual([os.path.basename(p) for p in paths], ["text2img_1.png", "text2img_2.png"])


if __name__ == "__main__":
    unittest.main()
