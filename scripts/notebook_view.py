# scripts/notebook_view.py
# Автор: genai_colab. Показ галереи Gradio внутри ячейки Colab (встроенное окно), без поиска ссылок.


import html
import os
import socket
from urllib.parse import urlencode


def server_running(port=7860, timeout=0.3):
    """Слушает ли локальный порт (запущена ли галерея Gradio в этой среде)."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def colab_base_url(port=7860):
    """Адрес сервера снаружи: прокси Colab, а вне Colab localhost."""
    try:
        from google.colab.output import eval_js
        return str(eval_js(f"google.colab.kernel.proxyPort({port})")).rstrip("/")
    except Exception:
        return f"http://localhost:{port}"


def gallery_url(image_path, base_url=None, running=None, port=7860):
    """Ссылка на страницу галереи, открывающая вкладку режима и эту картинку. None, если сервер не запущен."""
    if running is None:
        running = server_running(port)
    if not running:
        return None
    base = (base_url or colab_base_url(port)).rstrip("/")
    mode = os.path.basename(os.path.dirname(image_path))
    name = os.path.splitext(os.path.basename(image_path))[0]
    return f"{base}/?{urlencode({'mode': mode, 'img': name})}"


def gallery_link_html(image_path, base_url=None, running=None, port=7860):
    """HTML рядом с миниатюрой: ссылка на эту картинку в галерее или подсказка, как запустить галерею."""
    url = gallery_url(image_path, base_url, running, port)
    if url:
        return f'<a href="{html.escape(url, quote=True)}" target="_blank">🔎 Открыть в галерее: seed, промпт, скачать</a>'
    return "<small>Галерея не запущена: запусти ячейку 🌐 Gradio, и здесь появится ссылка на этот кадр.</small>"


def show_inline(port=7860, height=700, colab_output=None):
    """Открывает локальный сервер на порту port прямо под ячейкой. Вне Colab печатает адрес."""
    if colab_output is None:
        try:
            from google.colab import output as colab_output
        except ImportError:
            colab_output = False
    if colab_output is False:
        print(f"ℹ️ Вне Colab: открой http://localhost:{port}")
        return False
    try:
        colab_output.serve_kernel_port_as_iframe(port, height=height)
        return True
    except Exception as e:
        print(f"⚠️ Встроенное окно не открылось ({e}); открой сервер по ссылке из вывода выше (порт {port})")
        return False
