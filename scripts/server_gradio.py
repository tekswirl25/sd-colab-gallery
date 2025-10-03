import gradio as gr
import os
from scripts.logger import get_last_logs
from scripts.gallery_manager import show_gallery
from scripts.utils_validators import validate_positive_int
from scripts.utils_version import is_gradio_v4_or_newer

# ----- функции -----



def conditional_logs(auto: bool):
    """Если автообновление включено — вернуть новые логи, иначе None (чтобы не обновлять)."""
    last = get_last_logs(50)
    return "\n".join(last) if auto else None

# def show_gallery(output_dir="/content/outputs"):
#     """Возвращает список путей к изображениям для галереи."""
#     if not os.path.exists(output_dir):
#         return []
#     files = sorted(os.listdir(output_dir))
#     return [os.path.join(output_dir, f) for f in files if f.lower().endswith((".png",".jpg",".jpeg"))]

# ----- сервер -----


def start_gradio_server(output_dir="/content/outputs", refresh_interval=5, LOG_LINES=50):
    # Валидация входных параметров централизованно
    refresh_interval = validate_positive_int(refresh_interval, 5, "refresh_interval")
    LOG_LINES = validate_positive_int(LOG_LINES, 50, "LOG_LINES")

    with gr.Blocks() as demo:
        # ── Logs tab ──────────────────────────────────────────────────────────────
        with gr.Tab("Logs"):
            auto_update = gr.Checkbox(
                label=f"Auto-refresh every {refresh_interval}s",
                value=False
            )
            refresh_btn = gr.Button("Refresh now")
            logs_box = gr.Textbox(
                label=f"Last {LOG_LINES} logs",
                lines=LOG_LINES,
                interactive=False
            )

            # Ручное обновление — используем уже существующую функцию get_last_logs
            refresh_btn.click(
                fn=lambda: "\n".join(get_last_logs(LOG_LINES)),
                outputs=logs_box
            )

            # Автообновление: вилка по версии Gradio (v3 vs v4+)
            if not is_gradio_v4_or_newer():
                # Gradio < 4: поддерживается every=
                demo.load(
                    fn=lambda auto: "\n".join(get_last_logs(LOG_LINES)) if auto else "",
                    inputs=auto_update,
                    outputs=logs_box,
                    every=refresh_interval
                )
            else:
                # Gradio >= 4: таймер
                timer = gr.Timer(refresh_interval, repeat=True)
                timer.tick(
                    fn=lambda auto: "\n".join(get_last_logs(LOG_LINES)) if auto else "",
                    inputs=auto_update,
                    outputs=logs_box
                )

        # ── Gallery tab ───────────────────────────────────────────────────────────
        with gr.Tab("Gallery"):
            gr.Gallery(show_gallery(output_dir), label="Generated Images") \
              .style(grid=[4], height="auto")

    return demo.launch(share=True, inline=False)
