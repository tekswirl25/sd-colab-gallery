import json
import os
import tempfile
import unittest

from PIL import Image

from tests import stubs

stubs.install()
from scripts import smoke_check  # noqa: E402


class FakeRunner:
    """Заменяет run_generation: запоминает вызовы, может падать на заданном режиме."""

    def __init__(self, fail_on=()):
        self.calls, self.fail_on = [], set(fail_on)

    def __call__(self, mode, positive, negative, config, output_dir, **kw):
        self.calls.append((mode, kw))
        if mode["id"] in self.fail_on:
            raise RuntimeError(f"boom {mode['id']}")
        path = os.path.join(output_dir, f"{mode['id']}.png")
        Image.new("RGB", (64, 64), "white").save(path)
        return path


MODES = {
    "editorial-vo": {"id": "editorial-vo", "mode_type": "text2img", "positive": "p", "negative": "n",
                     "steps": 30, "width": 1280, "height": 720, "cfg": 7.0},
    "stock-ref-comic": {"id": "stock-ref-comic", "mode_type": "controlnet", "positive": "p", "negative": "n",
                        "steps": 30, "width": 1280, "height": 720, "cfg": 7.0},
    "inpaint-anatomy": {"id": "inpaint-anatomy", "mode_type": "inpaint", "positive": "p", "negative": "n",
                        "steps": 30, "width": 1280, "height": 720, "cfg": 7.0},
}


class SmokeCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = os.path.join(self.tmp.name, "out")
        self.rep = os.path.join(self.tmp.name, "report")
        self.cfg = {"MODEL_VARIANT": "SD15", "DEVICE": "cpu", "DTYPE": "float32", "OUTPUT_DIR": self.out}

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, runner, modes=("editorial-vo", "stock-ref-comic", "inpaint-anatomy"), **kw):
        return smoke_check.run_smoke(
            mode_ids=modes, config=self.cfg, steps=kw.pop("steps", 8), size=kw.pop("size", 512),
            report_dir=self.rep, runner=runner, get_mode=MODES.get, **kw)

    def test_all_modes_pass_and_report_saved(self):
        r = FakeRunner()
        report = self.run_check(r)
        self.assertEqual([x["mode"] for x in report["results"]], list(MODES))
        self.assertTrue(all(x["ok"] for x in report["results"]))
        saved = [f for f in os.listdir(self.rep) if f.endswith(".json")]
        self.assertEqual(len(saved), 1)
        self.assertEqual(json.load(open(os.path.join(self.rep, saved[0]), encoding="utf-8"))["variant"], "SD15")

    def test_small_steps_and_size_override_mode_values(self):
        r = FakeRunner()
        self.run_check(r, steps=6, size=384)
        for mode, _ in r.calls:
            self.assertEqual((mode["steps"], mode["width"], mode["height"]), (6, 384, 384))
        self.assertEqual(MODES["editorial-vo"]["steps"], 30)  # исходные режимы не меняются

    def test_one_failure_does_not_stop_the_rest(self):
        r = FakeRunner(fail_on=["stock-ref-comic"])
        report = self.run_check(r)
        by = {x["mode"]: x for x in report["results"]}
        self.assertFalse(by["stock-ref-comic"]["ok"])
        self.assertIn("boom", by["stock-ref-comic"]["error"])
        self.assertTrue(by["inpaint-anatomy"]["ok"])

    def test_source_for_controlnet_and_inpaint_is_first_output_and_mask_is_made(self):
        r = FakeRunner()
        self.run_check(r)
        kw = dict((m["id"], k) for m, k in r.calls)
        first_out = os.path.join(self.out, "editorial-vo.png")
        self.assertEqual(kw["stock-ref-comic"]["src_path"], first_out)
        self.assertEqual(kw["inpaint-anatomy"]["src_path"], first_out)
        mask = Image.open(kw["inpaint-anatomy"]["mask_path"])
        self.assertEqual(mask.size, (512, 512))
        self.assertEqual(mask.convert("L").getpixel((256, 256)), 255)
        self.assertEqual(mask.convert("L").getpixel((2, 2)), 0)

    def test_dependent_modes_are_skipped_when_source_missing(self):
        r = FakeRunner(fail_on=["editorial-vo"])
        report = self.run_check(r)
        by = {x["mode"]: x for x in report["results"]}
        self.assertFalse(by["editorial-vo"]["ok"])
        for m in ("stock-ref-comic", "inpaint-anatomy"):
            self.assertFalse(by[m]["ok"])
            self.assertIn("нет исходного", by[m]["error"])
        self.assertEqual(len(r.calls), 1)

    def test_unknown_mode_is_reported_not_raised(self):
        report = self.run_check(FakeRunner(), modes=("nope",))
        self.assertFalse(report["results"][0]["ok"])

    def test_timing_and_vram_come_from_injected_probes(self):
        ticks = iter([10.0, 14.5, 20.0, 21.0, 30.0, 33.0])
        report = self.run_check(FakeRunner(), clock=lambda: next(ticks), peak_vram_gb=lambda: 4.2)
        self.assertEqual(report["results"][0]["seconds"], 4.5)
        self.assertEqual(report["results"][0]["peak_vram_gb"], 4.2)

    def test_summary_text_lists_every_mode_with_status(self):
        report = self.run_check(FakeRunner(fail_on=["inpaint-anatomy"]))
        text = smoke_check.format_report(report)
        for m in MODES:
            self.assertIn(m, text)
        self.assertIn("OK", text)
        self.assertIn("FAIL", text)


if __name__ == "__main__":
    unittest.main()
