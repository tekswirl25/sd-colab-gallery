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


# ───────────────────────── Img2Img, ControlNet, Inpaint, Upscale ─────────────────────────
class ModesBase(unittest.TestCase):
    DEFAULTS = {"img2img_steps": 25, "img2img_cfg": 7.0, "controlnet_steps": 20, "controlnet_cfg": 6.0,
                "inpaint_steps": 30, "inpaint_cfg": 7.5}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pipe = FakePipe()
        self.pipe_args, self.saved = [], []
        self.config = {"MODEL_VARIANT": "SD15", "DEVICE": "cpu", "DTYPE": "float32", "OUTPUT_DIR": self.tmp.name}
        self.src = self.image("src.png", (64, 48))
        self.mask = self.image("mask.png", (32, 24), "white")

    def tearDown(self):
        self.tmp.cleanup()

    def image(self, name, size, color="gray"):
        p = os.path.join(self.tmp.name, name)
        Image.new("RGB", size, color).save(p)
        return p

    def get_pipe(self, *a):
        self.pipe_args.append(a)
        return self.pipe

    def save(self, im, prefix, meta, output_dir, mode):
        self.saved.append((prefix, meta, output_dir, mode))
        return os.path.join(output_dir, f"{prefix}.png"), os.path.join(output_dir, f"{prefix}.json")


class Img2ImgTest(ModesBase):
    def run_it(self, **kw):
        args = dict(config=self.config, defaults=self.DEFAULTS, user_prompt="a cat", seed=7, strength=0.6,
                    base_style="illustration", color_tone="vintage", style_extra="1940s", negative="anime",
                    src_path=self.src, get_pipe=self.get_pipe, save=self.save)
        args.update(kw)
        return generate.run_img2img(**args)

    def test_pipe_call_uses_defaults_prompt_and_source_image(self):
        self.run_it()
        self.assertEqual(self.pipe_args[0][0], "stable-diffusion-v1-5/stable-diffusion-v1-5")
        kw = self.pipe.calls[0]
        self.assertEqual((kw["num_inference_steps"], kw["guidance_scale"], kw["strength"]), (25, 7.0, 0.6))
        self.assertEqual(kw["negative_prompt"], "anime")
        self.assertEqual(kw["image"].size, (64, 48))
        self.assertTrue(kw["prompt"].startswith("a cat"))
        self.assertIn("hand-drawn", kw["prompt"])   # base_style из presets/styles.json
        self.assertTrue(kw["prompt"].endswith("1940s"))
        self.assertEqual(kw["generator"].seed, 7)

    def test_saved_as_img2img_with_meta_and_returns_paths(self):
        paths = self.run_it()
        prefix, meta, out, mode = self.saved[0]
        self.assertEqual((prefix, mode, out), ("img2img", "img2img", self.tmp.name))
        self.assertEqual(meta["source_path"], self.src)
        self.assertEqual((meta["strength"], meta["seed"], meta["mode"]), (0.6, 7, "img2img"))
        self.assertEqual([os.path.basename(p) for p in paths], ["img2img.png", "img2img.json"])

    def test_empty_negative_becomes_none(self):
        self.run_it(negative="")
        self.assertIsNone(self.pipe.calls[0]["negative_prompt"])

    def test_missing_source_gives_clear_errors(self):
        from scripts import notebook_uploads
        notebook_uploads.PATHS.clear()
        with self.assertRaisesRegex(ValueError, "Upload"):
            self.run_it(src_path=None)
        with self.assertRaises(FileNotFoundError):
            self.run_it(src_path=os.path.join(self.tmp.name, "nope.png"))

    def test_source_defaults_to_uploaded_path(self):
        from scripts import notebook_uploads
        notebook_uploads.PATHS["img2img"] = self.src
        self.run_it(src_path=None)
        self.assertEqual(self.saved[0][1]["source_path"], self.src)
        notebook_uploads.PATHS.clear()


class ControlNetTest(ModesBase):
    def run_it(self, **kw):
        self.canny_calls = []

        def canny(im, low, high):
            self.canny_calls.append((im.size, low, high))
            return Image.new("L", im.size, 128)

        args = dict(config=self.config, defaults=self.DEFAULTS, user_prompt="a cat", seed=7, low_thr=100,
                    high_thr=200, base_style=None, color_tone=None, style_extra="", negative="",
                    control_path=self.src, get_pipe=self.get_pipe, save=self.save, canny=canny)
        args.update(kw)
        return generate.run_controlnet(**args)

    def test_models_and_defaults(self):
        self.run_it()
        model_id, controlnet_id = self.pipe_args[0][0], self.pipe_args[0][1]
        self.assertEqual(model_id, "stable-diffusion-v1-5/stable-diffusion-v1-5")
        self.assertEqual(controlnet_id, "lllyasviel/sd-controlnet-canny")
        kw = self.pipe.calls[0]
        self.assertEqual((kw["num_inference_steps"], kw["guidance_scale"]), (20, 6.0))

    def test_turbo_uses_sdxl_base_for_controlnet(self):
        self.config["MODEL_VARIANT"] = "SDXL_TURBO"
        self.run_it()
        self.assertEqual(self.pipe_args[0][0], "stabilityai/stable-diffusion-xl-base-1.0")

    def test_control_image_is_the_canny_map_not_the_photo(self):
        # image= у ControlNet-пайплайна и есть карта контуров; фото как image превращало её в «управляющую»
        self.run_it(low_thr=50, high_thr=150)
        self.assertEqual(self.canny_calls, [((64, 48), 50, 150)])
        kw = self.pipe.calls[0]
        self.assertEqual(kw["image"].mode, "L")
        self.assertNotIn("control_image", kw)

    def test_meta_has_canny_thresholds_and_prefix(self):
        self.run_it(low_thr=50, high_thr=150)
        prefix, meta, _, mode = self.saved[0]
        self.assertEqual((prefix, mode), ("controlnet", "controlnet"))
        self.assertEqual(meta["canny"], {"low": 50, "high": 150})
        self.assertEqual(meta["source_path"], self.src)

    def test_missing_control_image(self):
        from scripts import notebook_uploads
        notebook_uploads.PATHS.clear()
        with self.assertRaisesRegex(ValueError, "Upload"):
            self.run_it(control_path=None)


class InpaintTest(ModesBase):
    def run_it(self, **kw):
        args = dict(config=self.config, defaults=self.DEFAULTS, user_prompt="fix hands", seed=7, strength=0.99,
                    base_style=None, color_tone=None, style_extra="", negative="", src_path=self.src,
                    mask_path=self.mask, get_pipe=self.get_pipe, save=self.save)
        args.update(kw)
        return generate.run_inpaint(**args)

    def test_mask_is_resized_to_image_and_params_come_from_defaults(self):
        self.run_it()
        kw = self.pipe.calls[0]
        self.assertEqual(kw["mask_image"].size, kw["image"].size)
        self.assertEqual(kw["image"].size, (64, 48))
        self.assertEqual((kw["num_inference_steps"], kw["guidance_scale"], kw["strength"]), (30, 7.5, 0.99))
        self.assertEqual(self.pipe_args[0][0], "runwayml/stable-diffusion-inpainting")

    def test_saved_as_inpaint_with_both_paths(self):
        self.run_it()
        prefix, meta, _, mode = self.saved[0]
        self.assertEqual((prefix, mode), ("inpaint", "inpaint"))
        self.assertEqual((meta["source_path"], meta["mask_path"]), (self.src, self.mask))

    def test_missing_image_or_mask(self):
        from scripts import notebook_uploads
        notebook_uploads.PATHS.clear()
        with self.assertRaisesRegex(ValueError, "image"):
            self.run_it(src_path=None)
        with self.assertRaisesRegex(ValueError, "mask"):
            self.run_it(mask_path=None)
        with self.assertRaises(FileNotFoundError):
            self.run_it(mask_path=os.path.join(self.tmp.name, "nope.png"))


class UpscaleTest(ModesBase):
    def run_it(self, **kw):
        args = dict(config=self.config, in_path=self.src, seed=7, prompt="", get_pipe=self.get_pipe, save=self.save)
        args.update(kw)
        return generate.run_upscale(**args)

    def test_upscale_model_prompt_and_save(self):
        path = self.run_it(prompt="sharp")
        self.assertEqual(self.pipe_args[0][0], "stabilityai/stable-diffusion-x4-upscaler")
        kw = self.pipe.calls[0]
        self.assertEqual((kw["prompt"], kw["generator"].seed), ("sharp", 7))
        prefix, meta, _, mode = self.saved[0]
        self.assertEqual((prefix, mode, meta["mode"]), ("upscale", "upscale", "upscale_x4"))
        self.assertEqual(os.path.basename(path), "upscale.png")

    def test_empty_path_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "in_path"):
            self.run_it(in_path="")
