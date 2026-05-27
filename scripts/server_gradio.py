import gradio as gr
import os

from scripts.logger import get_last_logs
from scripts.gallery_manager import show_gallery, delete_all, download_all
from scripts.utils_validators import validate_positive_int

# ----- функции -----



def conditional_logs(auto: bool, log_lines: int = 50):
    """Если автообновление включено — вернуть новые логи, иначе None (чтобы не обновлять)."""
    last = get_last_logs(log_lines)
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

            # Автообновление через Timer (Gradio 4+)
            timer = gr.Timer(refresh_interval)
            timer.tick(
                fn=lambda auto: conditional_logs(auto, LOG_LINES),
                inputs=auto_update,
                outputs=logs_box
            )

        # ── Gallery tab ───────────────────────────────────────────────────────────
        # 🔹 Галереи по модулям
        gallery_tabs = {
            "Text2Img": f"{output_dir}/text2img",
            "Img2Img": f"{output_dir}/img2img",
            "ControlNet": f"{output_dir}/controlnet"
        }

        for name, path in gallery_tabs.items():
            with gr.Tab(f"{name} Gallery"):
                os.makedirs(path, exist_ok=True)
                gallery = gr.Gallery(
                    value=show_gallery(path),
                    label=f"{name} Results",
                    columns=4,
                    height="auto"
                )
                refresh_gallery_btn = gr.Button("🔄 Refresh gallery")

                with gr.Row():
                    download_btn = gr.Button("⬇️ Download all")
                    delete_btn   = gr.Button("🗑️ Delete all")

                # Привязка кнопок (фиксируем path через аргумент)
                refresh_gallery_btn.click(fn=lambda p=path: show_gallery(p), outputs=gallery)
                download_btn.click(fn=lambda p=path: download_all(p), outputs=[])
                delete_btn.click(fn=lambda p=path: (delete_all(p), show_gallery(p))[1], outputs=gallery)



    return demo.launch(share=True, inline=False)
