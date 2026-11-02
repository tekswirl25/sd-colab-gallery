import gradio as gr
import os
from PIL import Image as PILImage

from scripts.logger import get_last_logs
from scripts.gallery_data import find_item, item_details, list_items, parse_link_query
from scripts.gallery_manager import delete_all_confirmed
from scripts.utils_validators import validate_positive_int


def _gallery_value(items):
    """Миниатюры с подписями «seed N · время». Миниатюры читаются как PIL: это обходит файловый сервер Gradio 6."""
    result = []
    for item in items:
        try:
            img = PILImage.open(item["thumb"] or item["image"]).convert("RGB")
            img.thumbnail((256, 256))
            result.append((img, item["caption"]))
        except Exception:
            pass
    return result


def _refresh(path):
    """Свежий список картинок режима: значение галереи и сами записи (для выбора картинки)."""
    items = list_items(path)
    return _gallery_value(items), items


def _textbox(label, **kw):
    """Поле с кнопкой копирования; если эта версия Gradio не знает параметра, обычное поле."""
    try:
        return gr.Textbox(label=label, show_copy_button=True, **kw)
    except TypeError:
        return gr.Textbox(label=label, **kw)


def start_gradio_server(output_dir="/content/outputs", refresh_interval=5, LOG_LINES=50):
    LOG_LINES = validate_positive_int(LOG_LINES, 50, "LOG_LINES")

    keys = {"text2img": "Text2Img", "img2img": "Img2Img", "controlnet": "ControlNet",
            "inpaint": "Inpaint", "upscale": "Upscale"}
    paths = {key: f"{output_dir}/{key}" for key in keys}
    panels = {}  # key -> (gallery, state, seed_box, prompt_box, params_box, file_box)

    with gr.Blocks() as demo:
        with gr.Tabs() as tabs:

            # ── Logs tab ──────────────────────────────────────────────────────────────
            with gr.Tab("Logs", id="logs"):
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
            for key, name in keys.items():
                path = paths[key]
                os.makedirs(path, exist_ok=True)
                items = list_items(path)
                with gr.Tab(f"{name} Gallery", id=key):
                    state = gr.State(value=items)
                    gallery = gr.Gallery(
                        value=_gallery_value(items),
                        label=f"{name} results",
                        columns=6,
                        rows=2,
                        height=420,
                        object_fit="contain",
                    )
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Refresh")
                        confirm_cb  = gr.Checkbox(label="Подтверждаю удаление всех картинок", value=False)
                        delete_btn  = gr.Button("🗑️ Delete all")

                    # Выбери миниатюру: ниже появятся seed и промпт (копируются кнопкой) и файл для скачивания
                    with gr.Row():
                        seed_box = _textbox("Seed", interactive=False, lines=1)
                        file_box = gr.File(label="Скачать оригинал", interactive=False)
                    prompt_box = _textbox("Prompt", interactive=False, lines=3)
                    params_box = _textbox("Параметры", interactive=False, lines=6)
                    panels[key] = (gallery, state, seed_box, prompt_box, params_box, file_box)

                    def on_select(items_now, evt: gr.SelectData):
                        index = getattr(evt, "index", None)
                        if isinstance(index, (list, tuple)):
                            index = index[0]
                        item = items_now[index] if isinstance(index, int) and 0 <= index < len(items_now) else None
                        d = item_details(item)
                        return d["seed"], d["prompt"], d["params"], d["file"]

                    gallery.select(on_select, inputs=[state], outputs=[seed_box, prompt_box, params_box, file_box])
                    refresh_btn.click(fn=lambda p=path: _refresh(p), outputs=[gallery, state])
                    delete_btn.click(
                        fn=lambda ok, p=path: (delete_all_confirmed(p, ok), *_refresh(p))[1:],
                        inputs=confirm_cb,
                        outputs=[gallery, state]
                    ).then(fn=lambda: False, outputs=confirm_cb)

        # ── Ссылка из ноутбука: ?mode=text2img&img=имя открывает вкладку и эту картинку ────────
        def on_load(request: gr.Request):
            skip = getattr(gr, "skip", None) or gr.update
            result = [skip()] * (1 + 6 * len(keys))
            link = parse_link_query(getattr(request, "query_params", None), list(keys))
            if not link:
                return result
            mode, name = link
            items = list_items(paths[mode])
            index = find_item(items, name)
            if index is None:
                return result
            d = item_details(items[index])
            base = 1 + 6 * list(keys).index(mode)
            result[0] = gr.update(selected=mode)
            result[base] = gr.update(value=_gallery_value(items), selected_index=index)
            result[base + 1] = items
            result[base + 2:base + 6] = [d["seed"], d["prompt"], d["params"], d["file"]]
            return result

        demo.load(on_load, inputs=None,
                  outputs=[tabs] + [comp for key in keys for comp in panels[key]])

    subdirs = [output_dir] + [
        os.path.join(output_dir, d)
        for d in ("text2img", "img2img", "controlnet", "inpaint", "upscale", "thumbnails")
    ]
    demo.launch(share=False, inline=False, server_port=7860,
                quiet=True, allowed_paths=subdirs)
    try:
        from google.colab.output import eval_js
        url = eval_js("google.colab.kernel.proxyPort(7860)")
        print(f"✅ Gradio server: {url}")
    except Exception:
        print("✅ Gradio server running at http://localhost:7860")
