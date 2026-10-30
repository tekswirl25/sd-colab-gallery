import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

from tests import stubs

stubs.install()


class FakePipe:
    """Запоминает, с чем его вызвали, и возвращает белую картинку."""

    def __init__(self, tag):
        self.tag, self.calls, self.ip_loaded = tag, [], 0

    def __call__(self, **kw):
        self.calls.append(kw)
        return types.SimpleNamespace(images=[Image.new("RGB", (64, 64), "white")])

    def load_ip_adapter(self, *a, **k):
        self.ip_loaded += 1

    def set_ip_adapter_scale(self, s):
        pass

    def unload_ip_adapter(self):
        self.ip_unloaded = True


def install_fake_heavy_modules(log):
    loaders = types.ModuleType("scripts.loaders")
    loaders.get_txt2img_pipe = lambda m, d, t: log.setdefault("txt2img", (m, FakePipe("t2i")))[1]
    loaders.get_img2img_pipe = lambda m, d, t: log.setdefault("img2img", (m, FakePipe("i2i")))[1]
    loaders.get_inpaint_pipe = lambda m, d, t: log.setdefault("inpaint", (m, FakePipe("inp")))[1]
    loaders.get_controlnet_pipe = lambda m, c, d, t: log.setdefault("controlnet", (m, c, FakePipe("cn")))[2]
    utils = types.ModuleType("scripts.utils")
    utils.canny_from_image = lambda im, low=100, high=200: im
    utils.save_image_and_meta = lambda im, prefix, meta, out, mode="text2img": (
        log.__setitem__("saved", (prefix, meta, out, mode)) or str(Path(out) / "x.png"), "x.json")
    sys.modules["scripts.loaders"] = loaders
    sys.modules["scripts.utils"] = utils


class UsaSafariTestBase(unittest.TestCase):
    def setUp(self):
        self.log = {}
        install_fake_heavy_modules(self.log)
        sys.modules.pop("scripts.usa_safari", None)
        from scripts import usa_safari
        self.m = usa_safari
        self._cwd = os.getcwd()
        os.chdir(stubs.ROOT)  # PRESETS_DIR относительный
        self.tmp = tempfile.TemporaryDirectory()
        # seeds_log на Drive не должен писать в тест
        self.m.SEEDS_LOG = Path(self.tmp.name) / "seeds" / "seeds_log.txt"

    def tearDown(self):
        os.chdir(self._cwd)
        self.tmp.cleanup()
        for k in ("scripts.loaders", "scripts.utils"):
            sys.modules.pop(k, None)

    def cfg(self, variant="SD15"):
        return {"MODEL_VARIANT": variant, "DEVICE": "cpu", "DTYPE": "float32", "OUTPUT_DIR": self.tmp.name}

    def img(self, name, size=(200, 100), color="gray"):
        p = os.path.join(self.tmp.name, name)
        Image.new("RGB", size, color).save(p)
        return p


class ModesFileTest(UsaSafariTestBase):
    def test_seven_modes_with_unique_ids(self):
        ids = [m["id"] for m in self.m.list_modes()]
        self.assertEqual(len(ids), 7)
        self.assertEqual(len(set(ids)), 7)

    def test_each_mode_is_runnable(self):
        for m in self.m.list_modes():
            self.assertIn(m["mode_type"], {"text2img", "img2img", "controlnet", "inpaint"}, m["id"])
            for k in ("label", "positive", "negative", "steps", "cfg", "width", "height", "seed"):
                self.assertIn(k, m, f'{m["id"]}.{k}')
            if m["mode_type"] == "controlnet":
                self.assertIn(m["controlnet_type"], {"canny", "openpose", "depth"}, m["id"])
            if m["mode_type"] == "inpaint":
                self.assertIsNotNone(m["denoising"], m["id"])

    def test_get_mode(self):
        self.assertEqual(self.m.get_mode("editorial-vo")["mode_type"], "text2img")
        self.assertIsNone(self.m.get_mode("nope"))

    def test_notebook_dropdown_ids_exist_in_modes(self):
        nb = json.load(open(stubs.ROOT / "colab" / "SDXL_Vintage_Illustration_FULL_Pro_Turbo_Gallery.ipynb"))
        src = next("".join(c["source"]) for c in nb["cells"] if "USA Safari — Генератор" in "".join(c["source"])[:80])
        ids = {m["id"] for m in self.m.list_modes()}
        for mid in ids:
            self.assertIn(f'"{mid}"', src, mid)


class BuildPromptsTest(UsaSafariTestBase):
    def test_without_character_has_no_anatomy(self):
        mode = self.m.get_mode("editorial-vo")
        pos, neg = self.m.build_prompts(mode, "a senator at a podium", False)
        self.assertTrue(pos.startswith(mode["positive"]))
        self.assertIn("a senator at a podium", pos)
        self.assertNotIn(mode["anatomy_addon"], pos)
        self.assertEqual(neg, mode["negative"])

    def test_with_character_adds_anatomy_both_sides(self):
        mode = self.m.get_mode("editorial-vo")
        pos, neg = self.m.build_prompts(mode, "x", True)
        self.assertIn(mode["anatomy_addon"], pos)
        self.assertIn(mode["anatomy_negative"], neg)

    def test_inpaint_mode_has_no_addon_and_does_not_crash(self):
        mode = self.m.get_mode("inpaint-anatomy")
        pos, neg = self.m.build_prompts(mode, "", True)
        self.assertEqual(pos, mode["positive"])
        self.assertEqual(neg, mode["negative"])


class ParseBriefTest(UsaSafariTestBase):
    FULL = (
        "[Inpaint Anatomy]\n"
        "Сцена: сенатор у трибуны\n"
        "Персонаж: да\n"
        "Если да: силуэт, 50 лет\n"
        "Исходник: есть (тип: screenshot)\n"
        "IP-Adapter: да (ref: Official_Canonical.jpg)\n"
    )

    def test_full_brief(self):
        r = self.m.parse_scene_brief(self.FULL)
        self.assertEqual(r["mode_id"], "inpaint-anatomy")
        self.assertEqual(r["scene"], "сенатор у трибуны")
        self.assertTrue(r["with_character"])
        self.assertEqual(r["character_desc"], "силуэт, 50 лет")
        self.assertTrue(r["has_source"])
        self.assertEqual(r["source_type"], "screenshot")
        self.assertTrue(r["use_ip_adapter"])

    def test_ip_reference_filename_keeps_case(self):
        # Drive различает регистр: имя файла нельзя приводить к нижнему
        r = self.m.parse_scene_brief(self.FULL)
        self.assertEqual(r["ip_ref_name"], "Official_Canonical.jpg")

    def test_no_source_defaults_to_editorial(self):
        r = self.m.parse_scene_brief("Сцена: улица\nПерсонаж: нет\nИсходник: нет")
        self.assertEqual(r["mode_id"], "editorial-vo")
        self.assertFalse(r["has_source"])

    def test_source_type_selects_mode_when_no_mode_line(self):
        r = self.m.parse_scene_brief("Сцена: улица\nИсходник: есть (тип: video frame)")
        self.assertEqual(r["mode_id"], "roto-video-frame")

    def test_scene_text_is_never_taken_as_mode(self):
        # слово из сцены ("face", "news", "video") не должно выбирать режим
        r = self.m.parse_scene_brief("Сцена: close-up of a face on the news video\nПерсонаж: нет\nИсходник: нет")
        self.assertEqual(r["mode_id"], "editorial-vo")

    def test_every_alias_points_to_existing_mode(self):
        ids = {m["id"] for m in self.m.list_modes()}
        self.assertTrue(set(self.m._MODE_ALIASES.values()) <= ids)
        self.assertTrue(set(self.m._SOURCE_TYPE_MAP.values()) <= ids)


class RunGenerationTest(UsaSafariTestBase):
    def run_mode(self, mode_id, variant="SD15", **kw):
        mode = self.m.get_mode(mode_id)
        pos, neg = self.m.build_prompts(mode, "scene", False)
        out = self.m.run_generation(mode, pos, neg, self.cfg(variant), self.tmp.name, **kw)
        return mode, out

    def test_text2img_uses_variant_model_and_mode_params(self):
        mode, _ = self.run_mode("editorial-vo", "SDXL")
        model_id, pipe = self.log["txt2img"]
        self.assertEqual(model_id, "stabilityai/stable-diffusion-xl-base-1.0")
        call = pipe.calls[0]
        self.assertEqual((call["width"], call["height"]), (mode["width"], mode["height"]))
        self.assertEqual(call["num_inference_steps"], mode["steps"])

    def test_random_seed_is_saved_in_meta(self):
        self.run_mode("editorial-vo")
        self.assertEqual(self.log["saved"][1]["seed"], 123456789)

    def test_fixed_seed_is_used(self):
        mode = dict(self.m.get_mode("editorial-vo"), seed=42)
        self.m.run_generation(mode, "p", "n", self.cfg(), self.tmp.name)
        self.assertEqual(self.log["saved"][1]["seed"], 42)
        self.assertEqual(self.log["txt2img"][1].calls[0]["generator"].seed, 42)

    def test_controlnet_requires_source(self):
        with self.assertRaises(ValueError):
            self.run_mode("news-screenshot")

    def test_controlnet_canny_and_openpose_pick_model_by_type(self):
        src = self.img("s.png")
        self.run_mode("news-screenshot", "SD15", src_path=src)
        self.assertEqual(self.log["controlnet"][1], "lllyasviel/sd-controlnet-canny")
        self.log.clear()
        # openpose без controlnet_aux должен упасть на canny, а не на импорте
        self.run_mode("stock-ref-comic", "SD15", src_path=src)
        self.assertEqual(self.log["controlnet"][1], "lllyasviel/control_v11p_sd15_openpose")

    def test_controlnet_receives_control_image_resized_to_mode_size(self):
        src = self.img("s.png", (333, 111))
        mode, _ = self.run_mode("news-screenshot", "SD15", src_path=src)
        got = self.log["controlnet"][2].calls[0]["image"]
        self.assertEqual(got.size, (mode["width"], mode["height"]))

    def test_turbo_controlnet_uses_sdxl_base_not_turbo(self):
        # как в ноутбуке (ячейка ControlNet): для SDXL_TURBO база ControlNet — controlnet_model
        self.run_mode("news-screenshot", "SDXL_TURBO", src_path=self.img("s.png"))
        self.assertEqual(self.log["controlnet"][0], "stabilityai/stable-diffusion-xl-base-1.0")

    def test_inpaint_needs_source_and_mask(self):
        with self.assertRaises(ValueError):
            self.run_mode("inpaint-face", src_path=self.img("s.png"))
        with self.assertRaises(ValueError):
            self.run_mode("inpaint-face", mask_path=self.img("m.png"))

    def test_inpaint_size_is_made_multiple_of_8_for_image_and_mask(self):
        src, mask = self.img("s.png", (203, 117)), self.img("m.png", (203, 117), "white")
        self.run_mode("inpaint-face", src_path=src, mask_path=mask)
        call = self.log["inpaint"][1].calls[0]
        self.assertEqual(call["image"].size, (200, 112))
        self.assertEqual(call["mask_image"].size, (200, 112))

    def test_inpaint_model_per_variant(self):
        self.run_mode("inpaint-face", "SD15", src_path=self.img("s.png"), mask_path=self.img("m.png"))
        self.assertEqual(self.log["inpaint"][0], "runwayml/stable-diffusion-inpainting")

    def test_unknown_mode_type_raises(self):
        with self.assertRaises(ValueError):
            self.m.run_generation({"id": "x", "mode_type": "weird"}, "p", "n", self.cfg(), self.tmp.name)

    def test_seed_log_is_written_to_configured_path(self):
        self.run_mode("editorial-vo")
        self.assertTrue(self.m.SEEDS_LOG.exists())
        self.assertIn("seed=123456789", self.m.SEEDS_LOG.read_text(encoding="utf-8"))

    def test_ip_adapter_does_not_leak_into_next_call_without_reference(self):
        # pipe кэшируется; адаптер, загруженный для одного кадра, не должен
        # ломать следующий кадр без референса
        ref = self.img("ref.jpg")
        self.run_mode("editorial-vo", ip_ref_path=ref)
        pipe = self.log["txt2img"][1]
        self.assertEqual(pipe.ip_loaded, 1)
        self.run_mode("editorial-vo")
        self.assertNotIn("ip_adapter_image", pipe.calls[1])
        self.assertTrue(getattr(pipe, "ip_unloaded", False),
                        "после кадра с IP-Adapter адаптер должен выгружаться (unload_ip_adapter)")

    def test_failed_ip_adapter_load_continues_without_reference(self):
        # сообщение «продолжаю без него» должно быть правдой: ip_adapter_image не передаётся
        def boom(*a, **k):
            raise OSError("no network")
        ref = self.img("ref.jpg")
        self.run_mode("editorial-vo")  # создать pipe в кэше
        self.log["txt2img"][1].load_ip_adapter = boom
        self.run_mode("editorial-vo", ip_ref_path=ref)
        self.assertNotIn("ip_adapter_image", self.log["txt2img"][1].calls[1])


if __name__ == "__main__":
    unittest.main()
