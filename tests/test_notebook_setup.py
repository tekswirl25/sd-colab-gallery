import os
import sys
import tempfile
import types
import unittest

from tests import stubs

stubs.install()
from scripts import notebook_setup  # noqa: E402


class InstallTest(unittest.TestCase):
    def run_install(self, fail_on=()):
        cmds = []

        def run(cmd):
            cmds.append(cmd)
            if any(f in " ".join(cmd) for f in fail_on):
                raise RuntimeError("pip failed")

        notebook_setup.install_dependencies("GPU_OPTIMAL", run=run)
        return [" ".join(c) for c in cmds]

    def test_installs_core_stack_with_upgrade_and_helpers(self):
        cmds = self.run_install()
        text = "\n".join(cmds)
        for pkg in ("diffusers", "transformers", "accelerate", "safetensors", "gradio", "opencv-python-headless",
                    "pillow", "ipywidgets", "packaging", "pyyaml", "controlnet_aux", "xformers"):
            self.assertIn(pkg, text, pkg)
        self.assertTrue(any("--upgrade" in c and "diffusers" in c for c in cmds))

    def test_optional_packages_do_not_stop_the_install(self):
        cmds = self.run_install(fail_on=("xformers", "controlnet_aux"))
        self.assertTrue(any("pyyaml" in c for c in cmds))

    def test_required_package_failure_is_raised(self):
        with self.assertRaises(RuntimeError):
            self.run_install(fail_on=("diffusers",))


class MountTest(unittest.TestCase):
    def test_mounts_sets_cache_env_and_makes_dir(self):
        old = {k: os.environ.get(k) for k in ("HF_HOME", "HUGGINGFACE_HUB_CACHE")}
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "hf")
            mounted = []
            try:
                got = notebook_setup.mount_drive_and_cache("/content/drive", cache, mount=mounted.append)
                self.assertEqual(mounted, ["/content/drive"])
                self.assertEqual(got, cache)
                self.assertTrue(os.path.isdir(cache))
                self.assertEqual((os.environ["HF_HOME"], os.environ["HUGGINGFACE_HUB_CACHE"]), (cache, cache))
            finally:
                for k, v in old.items():
                    os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_cache_on_drive_is_refused(self):
        # символьные ссылки кеша HF на Google Drive превращаются в текстовые файлы
        with self.assertRaisesRegex(ValueError, "Drive"):
            notebook_setup.mount_drive_and_cache("/content/drive", "/content/drive/MyDrive/hf_cache", mount=lambda m: None)


class InitConfigTest(unittest.TestCase):
    def test_missing_repo_gives_clear_message(self):
        with self.assertRaisesRegex(RuntimeError, "Старт"):
            notebook_setup.init_notebook_config("/no/such/dir", "SD15", "GPU_OPTIMAL", "/out", init_config=lambda **k: None)

    def test_adds_repo_to_sys_path_and_passes_params(self):
        seen = {}

        def init_config(**kw):
            seen.update(kw)
            return "CONFIG", "VARIANT", "DEFAULTS", "AUTO"

        with tempfile.TemporaryDirectory() as d:
            res = notebook_setup.init_notebook_config(d, "SDXL", "CPU", "/out", init_config=init_config,
                                                       get_token=lambda: "tok")
            self.assertIn(d, sys.path)
            sys.path.remove(d)
        self.assertEqual(res, ("CONFIG", "VARIANT", "DEFAULTS", "AUTO"))
        self.assertEqual(seen, {"model_variant": "SDXL", "output_dir": "/out", "hf_token": "tok", "mode": "CPU"})

    def test_token_lookup_failure_means_no_token(self):
        def boom():
            raise KeyError("no secret")

        seen = {}
        with tempfile.TemporaryDirectory() as d:
            notebook_setup.init_notebook_config(d, "SD15", "CPU", "/out", init_config=lambda **k: seen.update(k) or (1, 2, 3, 4),
                                                get_token=boom)
            if d in sys.path:
                sys.path.remove(d)
        self.assertIsNone(seen["hf_token"])


class SetupAllTest(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(stubs.ROOT)  # presets/ читается по относительному пути, как в Colab после chdir в репозиторий

    def tearDown(self):
        os.chdir(self._cwd)

    def test_runs_steps_in_order_and_returns_notebook_variables(self):
        order = []
        res = notebook_setup.setup_all(
            "/repo", "SD15", "GPU_OPTIMAL", "/out", "/content/drive", "/content/hf_cache",
            mount=lambda m: order.append("mount"),
            install=lambda mode: order.append("install"),
            init=lambda *a: order.append("init") or ({"OUTPUT_DIR": "/out"}, "V", {"d": 1}, True),
            preload=lambda: order.append("preload") or {"free_memory": "fm", "reset_pipes": "rp"})
        self.assertEqual(order, ["mount", "install", "init", "preload"])
        self.assertEqual(res["CONFIG"], {"OUTPUT_DIR": "/out"})
        self.assertEqual((res["VARIANT"], res["DEFAULTS"], res["AUTO_UPSCALE"]), ("V", {"d": 1}, True))
        self.assertEqual((res["free_memory"], res["reset_pipes"]), ("fm", "rp"))

    def test_returns_style_defaults_so_the_style_cell_is_really_optional(self):
        # режимы читают style_extra, negative и другие; без ячейки «Стиль и проект» они должны существовать
        res = notebook_setup.setup_all("/repo", "SD15", "CPU", "/out", "/content/drive", "/content/hf_cache",
                                       mount=lambda m: None, install=lambda m: None,
                                       init=lambda *a: ({"OUTPUT_DIR": "/out"}, 1, 2, 3), preload=lambda: {})
        for key in ("base_style", "color_tone", "negative", "style_extra", "style_suffix", "active_preset"):
            self.assertIn(key, res, key)
        self.assertEqual((res["base_style"], res["color_tone"], res["negative"], res["style_extra"]),
                         ("illustration", "vintage", "", ""))
        self.assertIsNone(res["active_preset"])
        self.assertIn("hand-drawn", res["style_suffix"])  # из presets/styles.json

    def test_prints_notebook_version_from_the_repo(self):
        import contextlib
        import io
        from scripts import notebook_version
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            notebook_setup.setup_all("/repo", "SD15", "CPU", "/out", "/content/drive", "/content/hf_cache",
                                     mount=lambda m: None, install=lambda m: None,
                                     init=lambda *a: ({"OUTPUT_DIR": "/out"}, 1, 2, 3), preload=lambda: {})
        self.assertIn(notebook_version.NOTEBOOK_VERSION, buf.getvalue())

    def test_cache_on_drive_stops_before_installing(self):
        order = []
        with self.assertRaises(ValueError):
            notebook_setup.setup_all("/repo", "SD15", "CPU", "/out", "/content/drive", "/content/drive/MyDrive/hf",
                                     mount=lambda m: order.append("mount"), install=lambda m: order.append("install"))
        self.assertEqual(order, [])


if __name__ == "__main__":
    unittest.main()
