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


class GalleryLinkTest(unittest.TestCase):
    def test_link_points_to_the_mode_and_image(self):
        url = notebook_view.gallery_url("/content/outputs/text2img/text2img_20261030_100000.png",
                                        base_url="https://x-7860.example/", running=True)
        self.assertEqual(url, "https://x-7860.example/?mode=text2img&img=text2img_20261030_100000")

    def test_base_without_trailing_slash(self):
        url = notebook_view.gallery_url("/o/img2img/img2img_1.png", base_url="http://localhost:7860", running=True)
        self.assertEqual(url, "http://localhost:7860/?mode=img2img&img=img2img_1")

    def test_no_link_when_the_server_is_not_running(self):
        self.assertIsNone(notebook_view.gallery_url("/o/text2img/a.png", base_url="http://localhost:7860", running=False))

    def test_html_has_a_link_that_opens_a_new_tab(self):
        html = notebook_view.gallery_link_html("/o/text2img/a.png", base_url="http://h:7860", running=True)
        self.assertIn('href="http://h:7860/?mode=text2img&amp;img=a"', html)  # & в HTML-атрибуте записывается как &amp;
        self.assertIn('target="_blank"', html)

    def test_link_looks_like_a_button(self):
        html = notebook_view.gallery_link_html("/o/text2img/a.png", base_url="http://h:7860", running=True)
        self.assertIn('role="button"', html)
        self.assertIn("border-radius", html)
        self.assertIn("background", html)

    def test_hint_without_a_running_gallery_is_a_disabled_button(self):
        html = notebook_view.gallery_link_html("/o/text2img/a.png", base_url="http://h:7860", running=False)
        self.assertIn('aria-disabled="true"', html)

    def test_html_hints_to_start_the_gallery_when_it_is_not_running(self):
        html = notebook_view.gallery_link_html("/o/text2img/a.png", base_url="http://h:7860", running=False)
        self.assertNotIn("href", html)
        self.assertIn("Gradio", html)

    def test_server_probe_detects_a_listening_port_and_a_closed_one(self):
        import socket
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        try:
            self.assertTrue(notebook_view.server_running(port))
        finally:
            srv.close()
        self.assertFalse(notebook_view.server_running(port))


if __name__ == "__main__":
    unittest.main()


class ThumbnailCardTest(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.image = Image.new("RGB", (30, 20), "red")

    def test_thumbnail_is_embedded_so_no_file_server_is_needed(self):
        html = notebook_view.thumbnail_card_html(self.image, "cap", "<a>go</a>")
        self.assertIn('src="data:image/jpeg;base64,', html)

    def test_button_comes_right_after_the_thumbnail_in_the_same_block(self):
        html = notebook_view.thumbnail_card_html(self.image, "cap", "<a>go</a>")
        self.assertLess(html.index("<img"), html.index("<a>go</a>"))

    def test_caption_is_escaped(self):
        html = notebook_view.thumbnail_card_html(self.image, "<b>x</b>", "")
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)

    def test_card_works_without_a_button(self):
        self.assertIn("<img", notebook_view.thumbnail_card_html(self.image, "cap", None))
