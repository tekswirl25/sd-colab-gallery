# scripts/notebook_view.py
# Автор: genai_colab. Показ галереи Gradio внутри ячейки Colab (встроенное окно), без поиска ссылок.


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
