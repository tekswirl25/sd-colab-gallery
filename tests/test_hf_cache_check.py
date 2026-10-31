import os
import tempfile
import unittest

from tests import stubs

stubs.install()
from scripts import hf_cache_check  # noqa: E402


def touch(path, data=b""):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


class CacheCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.c = self.tmp.name
        good = "models--org--good"
        bad = "models--org--bad"
        touch(f"{self.c}/{good}/blobs/aaa", b"weights")
        os.makedirs(f"{self.c}/{good}/snapshots/r1/text_encoder")
        os.symlink(f"{self.c}/{good}/blobs/aaa", f"{self.c}/{good}/snapshots/r1/text_encoder/model.bin")
        touch(f"{self.c}/{bad}/blobs/bbb", b"")                      # пустой blob
        os.makedirs(f"{self.c}/{bad}/snapshots/r1/unet")
        os.symlink(f"{self.c}/{bad}/blobs/bbb", f"{self.c}/{bad}/snapshots/r1/unet/model.bin")
        touch(f"{self.c}/.locks/{bad}/x.lock", b"")                  # служебные пустые файлы
        touch(f"{self.c}/{good}/refs/main", b"abc123")

    def tearDown(self):
        self.tmp.cleanup()


class FindTest(CacheCase):
    def test_finds_empty_blob_and_the_symlink_pointing_to_it(self):
        found = hf_cache_check.find_broken_files(self.c)
        names = sorted(os.path.basename(p) for p in found["empty"])
        self.assertEqual(names, ["bbb", "model.bin"])

    def test_lock_files_and_good_models_are_not_reported(self):
        found = hf_cache_check.find_broken_files(self.c)
        self.assertFalse([p for p in found["empty"] if ".locks" in p or "good" in p])

    def test_incomplete_downloads_are_reported_separately(self):
        touch(f"{self.c}/models--org--good/blobs/ccc.incomplete", b"half")
        found = hf_cache_check.find_broken_files(self.c)
        self.assertEqual([os.path.basename(p) for p in found["incomplete"]], ["ccc.incomplete"])

    def test_missing_cache_dir_gives_empty_result(self):
        found = hf_cache_check.find_broken_files(os.path.join(self.c, "nope"))
        self.assertEqual(found, {"empty": [], "incomplete": []})


class ModelsTest(CacheCase):
    def test_affected_models(self):
        found = hf_cache_check.find_broken_files(self.c)
        self.assertEqual(hf_cache_check.affected_models(found, self.c), ["models--org--bad"])

    def test_remove_deletes_only_listed_model_folders(self):
        removed = hf_cache_check.remove_models(["models--org--bad"], self.c)
        self.assertEqual(removed, ["models--org--bad"])
        self.assertFalse(os.path.exists(f"{self.c}/models--org--bad"))
        self.assertTrue(os.path.exists(f"{self.c}/models--org--good/blobs/aaa"))

    def test_remove_refuses_names_that_are_not_model_folders(self):
        for bad in ("../outside", "blobs", ".locks", "models--a/../../x", "/etc"):
            with self.assertRaises(ValueError):
                hf_cache_check.remove_models([bad], self.c)
        self.assertTrue(os.path.exists(f"{self.c}/.locks"))

    def test_report_says_what_to_do(self):
        found = hf_cache_check.find_broken_files(self.c)
        text = hf_cache_check.format_report(found, self.c, deleted=False)
        self.assertIn("models--org--bad", text)
        self.assertIn("DELETE_BROKEN", text)
        ok = hf_cache_check.format_report({"empty": [], "incomplete": []}, self.c, deleted=False)
        self.assertIn("пустых", ok)


if __name__ == "__main__":
    unittest.main()
