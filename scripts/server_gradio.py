import gradio as gr
import os

from scripts.logger import get_last_logs
from scripts.gallery_manager import show_gallery, delete_all, download_all
from scripts.utils_validators import validate_positive_int


def _gallery_value(path):
    """Возвращает список (filepath, caption) для gr.Gallery в Gradio 6."""
    return [(p, os.path.basename(p)) for p in show_gallery(path)]


def start_gradio_server(output_dir="/content/outputs", refresh_interval=5, LOG_LINES=50):
    LOG_LINES = validate_positive_int(LOG_LINES, 50, "LOG_LINES")

    with gr.Blocks() as demo:

        # ── Logs tab ──────────────────────────────────────────────────────────────
        with gr.Tab("Logs"):
            logs_box = gr.Textbox(
                label=f"Last {LOG_LINES} log lines",
                lines=LOG_LINES,
                interactive=False
            )
            refresh_logs_btn = gr.Button("🔄 Refresh logs")
            refresh_logs_btn.click(
                fn=lambda: "\n".join(get_last_logs(LOG_LINES)),
                outputs=logs_box
            )

        # ── Gallery tabs ──────────────────────────────────────────────────────────
        gallery_tabs = {
            "Text2Img":   f"{output_dir}/text2img",
            "Img2Img":    f"{output_dir}/img2img",
            "ControlNet": f"{output_dir}/controlnet",
        }

        for name, path in gallery_tabs.items():
            os.makedirs(path, exist_ok=True)
            with gr.Tab(f"{name} Gallery"):
                gallery = gr.Gallery(
                    value=_gallery_value(path),
                    label=f"{name} results",
                    columns=4,
                    height="auto",
                    show_download_button=True,
                )
                with gr.Row():
                    refresh_btn = gr.Button("🔄 Refresh")
                    delete_btn  = gr.Button("🗑️ Delete all")

                refresh_btn.click(fn=lambda p=path: _gallery_value(p), outputs=gallery)
                delete_btn.click(
                    fn=lambda p=path: (delete_all(p), _gallery_value(p))[1],
                    outputs=gallery
                )

    subdirs = [output_dir] + [
        os.path.join(output_dir, d)
        for d in ("text2img", "img2img", "controlnet", "upscale")
    ]
    return demo.launch(share=True, inline=False, allowed_paths=subdirs)
