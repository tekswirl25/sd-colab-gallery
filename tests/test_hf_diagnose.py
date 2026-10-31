import os
import tempfile
import types
import unittest
import zipfile

from tests import stubs

stubs.install()
from scripts import hf_diagnose  # noqa: E402


class FakeApi:
    def __init__(self, files, fail=False):
        self.files, self.fail, self.calls = files, fail, []

    def model_info(self, repo, files_metadata=False):
        self.calls.append((repo, files_metadata))
        if self.fail:
            raise OSError("no network")
        return types.SimpleNamespace(siblings=[types.SimpleNamespace(rfilename=n, size=s) for n, s in self.files])


class ListWeightsTest(unittest.TestCase):
    FILES = [("unet/diffusion_pytorch_model.bin", 3_400_000_000),
             ("unet/diffusion_pytorch_model.fp16.safetensors", 1_700_000_000),
             ("model_index.json", 500), ("sd-v1-5-inpainting.ckpt", 4_000_000_000),
             ("text_encoder/model.safetensors", 490_000_000)]

    def test_only_weight_files_with_format_and_pickle_flag(self):
        rows = hf_diagnose.list_weight_files("org/repo", FakeApi(self.FILES))
        by = {r["path"]: r for r in rows}
        self.assertNotIn("model_index.json", by)
        self.assertEqual(by["unet/diffusion_pytorch_model.bin"]["format"], "bin")
        self.assertTrue(by["unet/diffusion_pytorch_model.bin"]["pickle"])
        self.assertTrue(by["sd-v1-5-inpainting.ckpt"]["pickle"])
        self.assertFalse(by["text_encoder/model.safetensors"]["pickle"])
        self.assertEqual(by["unet/diffusion_pytorch_model.fp16.safetensors"]["size"], 1_700_000_000)

    def test_asks_for_file_sizes(self):
        api = FakeApi(self.FILES)
        hf_diagnose.list_weight_files("org/repo", api)
        self.assertEqual(api.calls, [("org/repo", True)])

    def test_network_error_is_returned_as_text_not_raised(self):
        rows = hf_diagnose.list_weight_files("org/repo", FakeApi([], fail=True))
        self.assertEqual(rows, [{"error": "OSError: no network"}])

    def test_format_table_mentions_safetensors_verdict(self):
        rows = hf_diagnose.list_weight_files("org/repo", FakeApi(self.FILES))
        text = hf_diagnose.format_weight_table("org/repo", rows)
        self.assertIn("org/repo", text)
        self.assertIn("safetensors: да", text)
        none = hf_diagnose.format_weight_table("a/b", [{"path": "x.bin", "format": "bin", "size": 1, "pickle": True}])
        self.assertIn("safetensors: нет", none)


class InspectLocalTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def path(self, name, data):
        p = os.path.join(self.d, name)
        open(p, "wb").write(data)
        return p

    def test_zip_file_is_recognised(self):
        p = os.path.join(self.d, "ok.bin")
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("archive/data.pkl", b"x")
        info = hf_diagnose.inspect_local_file(p)
        self.assertTrue(info["is_zip"])
        self.assertEqual(info["size"], os.path.getsize(p))
        self.assertTrue(info["head_hex"].startswith("504b0304"))

    def test_empty_file(self):
        info = hf_diagnose.inspect_local_file(self.path("e.bin", b""))
        self.assertEqual((info["size"], info["is_zip"], info["head_hex"]), (0, False, ""))

    def test_git_lfs_pointer_is_detected(self):
        info = hf_diagnose.inspect_local_file(self.path("p.bin", b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 3\n"))
        self.assertTrue(info["lfs_pointer"])

    def test_random_bytes_are_not_zip(self):
        info = hf_diagnose.inspect_local_file(self.path("r.bin", b"\x80\x02}q\x00." * 100))
        self.assertFalse(info["is_zip"])
        self.assertFalse(info["lfs_pointer"])

    def test_symlink_is_followed(self):
        real = self.path("real.bin", b"abc")
        link = os.path.join(self.d, "link.bin")
        os.symlink(real, link)
        self.assertEqual(hf_diagnose.inspect_local_file(link)["size"], 3)

    def test_missing_file(self):
        self.assertEqual(hf_diagnose.inspect_local_file(os.path.join(self.d, "no"))["error"], "файла нет")

    def test_verdict_compares_with_remote_size(self):
        base = {"size": 100, "is_zip": True, "lfs_pointer": False}
        self.assertIn("совпадает", hf_diagnose.verdict(base, remote_size=100))
        self.assertIn("обрезан", hf_diagnose.verdict(dict(base, size=40), remote_size=100))
        self.assertIn("пустой", hf_diagnose.verdict(dict(base, size=0, is_zip=False), remote_size=100))
        self.assertIn("git-lfs", hf_diagnose.verdict(dict(base, lfs_pointer=True, is_zip=False), remote_size=100))
        self.assertIn("не zip", hf_diagnose.verdict(dict(base, is_zip=False), remote_size=100))


if __name__ == "__main__":
    unittest.main()
