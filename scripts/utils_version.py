import gradio as gr
from packaging import version

def is_gradio_v4_or_newer() -> bool:
    """True для Gradio v4+, иначе False."""
    try:
        return version.parse(gr.__version__) >= version.parse("4.0.0")
    except Exception:
        return False
