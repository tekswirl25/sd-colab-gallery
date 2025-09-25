import gradio as gr
import os
from scripts.logger import get_last_logs

# ----- функции -----

def show_logs():
    """Возвращает последние 50 строк из лога."""
    last = get_last_logs(50)
    return "\n".join(last)

def conditional_logs(auto: bool):
    """Если автообновление включено — вернуть новые логи, иначе None (чтобы не обновлять)."""
    return show_logs() if auto else None

def show_gallery(output_dir="/content/outputs"):
    """Возвращает список путей к изображениям для галереи."""
    if not os.path.exists(output_dir):
        return []
    files = sorted(os.listdir(output_dir))
    return [os.path.join(output_dir, f) for f in files if f.lower().endswith((".png",".jpg",".jpeg"))]

# ----- сервер -----

def start_gradio_server(output_dir="/content/outputs"):
    with gr.Blocks() as demo:
        with gr.Tab("Logs"):
            auto_update = gr.Checkbox(label="Auto-refresh every 5s", value=False)
            refresh_btn = gr.Button("Refresh now")
            logs_box = gr.Textbox(value=show_logs(), lines=20, interactive=False, label="Last 50 logs")

            # Ручное обновление
            refresh_btn.click(fn=show_logs, outputs=logs_box)

            # Автообновление: каждые 5 секунд проверяем, включён ли чекбокс
            logs_box.load(fn=conditional_logs, inputs=auto_update, outputs=logs_box, every=5)

        with gr.Tab("Gallery"):
            gr.Gallery(show_gallery(output_dir), label="Generated Images").style(grid=[4], height="auto")

    launch_obj = demo.launch(share=True, inline=False)
    return launch_obj
