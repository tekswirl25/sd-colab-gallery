import gradio as gr
import os

from scripts.logger import get_last_logs
from scripts.gallery_data import (THUMB_SIDE, card_html, more_html, toggle, ticks_css, choices, delete_all, delete_many, find_item, grid_html, item_details,
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


PER_ROW = 6   # миниатюр в ряду
SHOWN = 48    # сколько последних кадров рисуется на режим


def _bump(view_now, all_on=False):
    """Новое состояние сетки: номер перерисовки растёт, поэтому старые отметки не прилипают к новым галочкам."""
    return {"gen": (view_now or {}).get("gen", 0) + 1, "all": all_on}


def _make_draw(key, ticked):
    """Функция для gr.render: под каждой миниатюрой её галочка; отмеченные имена копятся в состоянии ticked."""
    def draw(items_now, view_now):
        view_now = view_now or {}
        if not items_now:
            gr.HTML(value=grid_html([]))
            return
        gen, all_on = view_now.get("gen", 0), bool(view_now.get("all"))
        shown = items_now[:SHOWN]
        for start in range(0, len(shown), PER_ROW):
            with gr.Row():
                for number, item in enumerate(shown[start:start + PER_ROW], start + 1):
                    with gr.Column(min_width=THUMB_SIDE):
                        gr.HTML(value=card_html(item, number))
                        box = gr.Checkbox(label="выбрать", value=all_on, key=f"{key}_{gen}_{item['name']}")
                        box.change(fn=lambda on, cur, nm=item["name"]: toggle(cur, nm, on),
                                   inputs=[box, ticked], outputs=ticked)
        note = more_html(items_now, SHOWN)
        if note:
            gr.HTML(value=note)
    return draw


def _details(items, name):
    """Крупный просмотр, seed, prompt, параметры выбранного кадра; пусто, если кадра нет."""
    index = find_item(items, name) if name else None
    if index is None:
        return "", "", "", ""
    d = item_details(items[index])
    return view_html(items[index]), d["seed"], d["prompt"], d["params"]


def start_gradio_server(output_dir="/content/outputs", refresh_interval=5, LOG_LINES=50):
    LOG_LINES = validate_positive_int(LOG_LINES, 50, "LOG_LINES")
    # С gr.render под каждой миниатюрой своя галочка; в старом Gradio без него список галочек под сеткой.
    dynamic = hasattr(gr, "render")
    grid_value = (lambda items: "") if dynamic else grid_html
    ticks_value = (lambda items: []) if dynamic else _ticks_update

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
                    if dynamic:
                        vstate = gr.State(value={"gen": 0, "all": False})
                        ticks = gr.State(value=[])
                        grid = gr.HTML(value="", visible=False)  # заглушка: сетку рисует gr.render
                        gr.render(inputs=[state, vstate])(_make_draw(key, ticks))
                    else:
                        vstate = None
                        grid = gr.HTML(value=grid_html(items), elem_id=f"{key}_grid")
                        ticks = gr.CheckboxGroup(choices=tick_choices(items), value=[],
                                                 label="Отметить кадры (под своей миниатюрой)", elem_id=f"{key}_ticks")
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

                    if dynamic:
                        tick_all_btn.click(fn=lambda items_now, v: ([i["name"] for i in items_now], _bump(v, True)),
                                           inputs=[state, vstate], outputs=[ticks, vstate])
                        tick_none_btn.click(fn=lambda v: ([], _bump(v)), inputs=vstate, outputs=[ticks, vstate])
                    else:
                        tick_all_btn.click(fn=lambda items_now: [i["name"] for i in items_now],
                                           inputs=state, outputs=ticks)
                        tick_none_btn.click(fn=lambda: [], outputs=ticks)

                    extra_in = [vstate] if dynamic else []        # состояние сетки нужно только с gr.render
                    extra_out = [vstate] if dynamic else []

                    def refresh(*v, p=path):
                        fresh = list_items(p)
                        return (grid_value(fresh), fresh, _pick_update(fresh), ticks_value(fresh),
                                *([_bump(v[0])] if v else []))

                    def on_delete_selected(ok, ticked, cur, items_now, *v, p=path):
                        if ok and ticked:
                            delete_many(items_now, ticked)
                            fresh = list_items(p)
                            return (grid_value(fresh), fresh, _pick_update(fresh, cur), ticks_value(fresh),
                                    *([_bump(v[0])] if v else []), False)
                        return (gr.skip(),) * (5 + len(v))

                    def on_delete_all(ok, items_now, *v, p=path):
                        if ok:
                            delete_all(items_now)
                            fresh = list_items(p)
                            return (grid_value(fresh), fresh, _pick_update(fresh), ticks_value(fresh),
                                    *([_bump(v[0])] if v else []), False)
                        return (gr.skip(),) * (5 + len(v))

                    refresh_btn.click(fn=refresh, inputs=extra_in or None, outputs=[grid, state, pick, ticks, *extra_out])
                    delete_sel_btn.click(fn=on_delete_selected, inputs=[confirm_cb, ticks, pick, state, *extra_in],
                                         outputs=[grid, state, pick, ticks, *extra_out, confirm_cb])
                    delete_all_btn.click(fn=on_delete_all, inputs=[confirm_cb, state, *extra_in],
                                         outputs=[grid, state, pick, ticks, *extra_out, confirm_cb])

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
            result[base:base + 8] = [_pick_update(items, items[index]["name"]), items, grid_value(items),
                                     *_details(items, items[index]["name"]), ticks_value(items)]
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
