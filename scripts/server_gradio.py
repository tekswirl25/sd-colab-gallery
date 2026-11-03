import gradio as gr
import os

from scripts.logger import get_last_logs
from scripts.gallery_data import (ticks_css, choices, delete_all, delete_many, find_item, grid_html, item_details,
                                  list_items, neighbor, parse_link_query, tick_choices, view_html)
from scripts.utils_validators import validate_positive_int

# Картинки встроены в страницу, а не отдаются файловым сервером Gradio: в Colab его Gallery/File/Image
# приходят битыми (см. scripts/gallery_data.py). Файлы читаются и удаляются прямо в папке вывода (Drive).


def _textbox(label, **kw):
    """Поле с кнопкой копирования: Gradio 6 buttons=["copy"], старый show_copy_button, иначе обычное поле."""
    for extra in ({"buttons": ["copy"]}, {"show_copy_button": True}, {}):
        try:
            return gr.Textbox(label=label, **extra, **kw)
        except TypeError:
            continue
    return gr.Textbox(label=label, **kw)


def _logs_text(n):
    return "\n".join(line.rstrip("\n") for line in get_last_logs(n))


def _pick_update(items, name=None):
    """Обновление списка выбора: свежие варианты и кадр name (или первый)."""
    names = [i["name"] for i in items]
    value = name if name in names else (names[0] if names else None)
    return gr.update(choices=choices(items), value=value)


def _ticks_update(items):
    """Список отметок: свежие кадры, отметки сняты."""
    return gr.update(choices=tick_choices(items), value=[])


def _details(items, name):
    """Крупный просмотр, seed, prompt, параметры выбранного кадра; пусто, если кадра нет."""
    index = find_item(items, name) if name else None
    if index is None:
        return "", "", "", ""
    d = item_details(items[index])
    return view_html(items[index]), d["seed"], d["prompt"], d["params"]


def start_gradio_server(output_dir="/content/outputs", refresh_interval=5, LOG_LINES=50):
    LOG_LINES = validate_positive_int(LOG_LINES, 50, "LOG_LINES")

    keys = {"text2img": "Text2Img", "img2img": "Img2Img", "controlnet": "ControlNet",
            "inpaint": "Inpaint", "upscale": "Upscale"}
    paths = {key: f"{output_dir}/{key}" for key in keys}
    panels = {}  # key -> (pick, state, grid, view, seed_box, prompt_box, params_box, ticks)

    counts = {key: len(list_items(path)) for key, path in paths.items()}
    print(f"📂 Галерея смотрит папку: {output_dir} (Gradio {getattr(gr, '__version__', '?')})")
    print("🖼️ Уже есть: " + ", ".join(f"{keys[k]}: {n}" for k, n in counts.items()))

    with gr.Blocks() as demo:
        # стиль в HTML-блоке, а не в параметре Blocks: так работает в любой версии Gradio
        gr.HTML(value=f"<style>{ticks_css(list(keys))}</style>")
        with gr.Tabs() as tabs:

            # ── Logs tab ──────────────────────────────────────────────────────────────
            with gr.Tab("Logs", id="logs") as logs_tab:
                logs_box = gr.Textbox(
                    label=f"Last {LOG_LINES} log lines",
                    lines=LOG_LINES,
                    interactive=False
                )
                refresh_logs_btn = gr.Button("🔄 Refresh logs")
                refresh_logs_btn.click(fn=lambda: _logs_text(LOG_LINES), outputs=logs_box)
                logs_tab.select(fn=lambda: _logs_text(LOG_LINES), outputs=logs_box)

            # ── Gallery tabs ──────────────────────────────────────────────────────────
            for key, name in keys.items():
                path = paths[key]
                os.makedirs(path, exist_ok=True)
                items = list_items(path)
                first = items[0]["name"] if items else None
                with gr.Tab(f"{name} Gallery", id=key):
                    state = gr.State(value=items)
                    grid = gr.HTML(value=grid_html(items), elem_id=f"{key}_grid")
                    ticks = gr.CheckboxGroup(choices=tick_choices(items), value=[], label="Отметить кадры (под своей миниатюрой)",
                                             elem_id=f"{key}_ticks")
                    with gr.Row():
                        tick_all_btn = gr.Button("Отметить все")
                        tick_none_btn = gr.Button("Снять отметки")
                    pick = gr.Dropdown(choices=choices(items), value=first, label="Кадр",
                                       elem_id=f"{key}_pick", interactive=True)
                    with gr.Row():
                        prev_btn = gr.Button("◀ Назад")
                        next_btn = gr.Button("Вперёд ▶")
                        refresh_btn = gr.Button("🔄 Refresh")
                    view_value, seed_value, prompt_value, params_value = _details(items, first)
                    view = gr.HTML(value=view_value, elem_id=f"{key}_view")
                    seed_box = _textbox("Seed", interactive=False, lines=1, value=seed_value)
                    prompt_box = _textbox("Prompt", interactive=False, lines=3, value=prompt_value)
                    params_box = _textbox("Параметры", interactive=False, lines=6, value=params_value)
                    with gr.Row():
                        confirm_cb = gr.Checkbox(label="Подтверждаю удаление", value=False)
                        delete_sel_btn = gr.Button("🗑️ Delete selected")
                        delete_all_btn = gr.Button("🗑️ Delete all")
                    panels[key] = (pick, state, grid, view, seed_box, prompt_box, params_box, ticks)

                    pick.change(fn=_details, inputs=[state, pick], outputs=[view, seed_box, prompt_box, params_box])
                    next_btn.click(fn=lambda items_now, cur: neighbor(items_now, cur, +1),
                                   inputs=[state, pick], outputs=pick)
                    prev_btn.click(fn=lambda items_now, cur: neighbor(items_now, cur, -1),
                                   inputs=[state, pick], outputs=pick)

                    tick_all_btn.click(fn=lambda items_now: [i["name"] for i in items_now],
                                       inputs=state, outputs=ticks)
                    tick_none_btn.click(fn=lambda: [], outputs=ticks)

                    def refresh(p=path):
                        fresh = list_items(p)
                        return grid_html(fresh), fresh, _pick_update(fresh), _ticks_update(fresh)

                    def on_delete_selected(ok, ticked, cur, items_now, p=path):
                        if ok and ticked:
                            delete_many(items_now, ticked)
                            fresh = list_items(p)
                            return (grid_html(fresh), fresh, _pick_update(fresh, cur), _ticks_update(fresh), False)
                        return (gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip())

                    def on_delete_all(ok, items_now, p=path):
                        if ok:
                            delete_all(items_now)
                            fresh = list_items(p)
                            return (grid_html(fresh), fresh, _pick_update(fresh), _ticks_update(fresh), False)
                        return (gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip())

                    refresh_btn.click(fn=refresh, outputs=[grid, state, pick, ticks])
                    delete_sel_btn.click(fn=on_delete_selected, inputs=[confirm_cb, ticks, pick, state],
                                         outputs=[grid, state, pick, ticks, confirm_cb])
                    delete_all_btn.click(fn=on_delete_all, inputs=[confirm_cb, state],
                                         outputs=[grid, state, pick, ticks, confirm_cb])

        # ── Ссылка из ноутбука: ?mode=text2img&img=имя открывает вкладку и этот кадр ────────
        def on_load(request: gr.Request):
            skip = getattr(gr, "skip", None) or gr.update
            result = [skip()] * (1 + 8 * len(keys))
            link = parse_link_query(getattr(request, "query_params", None), list(keys))
            if not link:
                return result
            mode, name = link
            items = list_items(paths[mode])
            index = find_item(items, name)
            if index is None:
                return result
            base = 1 + 8 * list(keys).index(mode)
            result[0] = gr.update(selected=mode)
            result[base:base + 8] = [_pick_update(items, items[index]["name"]), items, grid_html(items),
                                     *_details(items, items[index]["name"]), _ticks_update(items)]
            return result

        demo.load(on_load, inputs=None,
                  outputs=[tabs] + [comp for key in keys for comp in panels[key]])
        demo.load(fn=lambda: _logs_text(LOG_LINES), outputs=logs_box)

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
