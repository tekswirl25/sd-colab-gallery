import types
import unittest

from tests import stubs

stubs.install()
from scripts import notebook_view  # noqa: E402


class ShowInlineTest(unittest.TestCase):
    def test_serves_the_port_inside_the_cell(self):
        calls = []
        out = types.SimpleNamespace(serve_kernel_port_as_iframe=lambda port, height=None: calls.append((port, height)))
        self.assertTrue(notebook_view.show_inline(7860, height=640, colab_output=out))
        self.assertEqual(calls, [(7860, 640)])

    def test_outside_colab_it_reports_and_does_not_raise(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ok = notebook_view.show_inline(7860, colab_output=False)
        self.assertFalse(ok)
        self.assertIn("7860", buf.getvalue())

    def test_iframe_failure_falls_back_to_a_message(self):
        def boom(port, height=None):
            raise RuntimeError("no iframe")
        out = types.SimpleNamespace(serve_kernel_port_as_iframe=boom)
        self.assertFalse(notebook_view.show_inline(7860, colab_output=out))


if __name__ == "__main__":
    unittest.main()
