# scripts/usa_safari_ui.py
# Автор: genai_colab. Интерфейс «USA Safari — Генератор» для Colab: выбор режима, бриф, сцена,
# загрузка исходника и маски, IP-Adapter, кнопка GENERATE. Раньше весь этот код лежал в ячейке
# ноутбука; в ячейке остаётся вызов show_generator(). Режимы берутся из presets/usa_safari_modes.json.
# Логика без виджетов вынесена в чистые функции (тесты без ipywidgets).

import os
import sys
import traceback
from types import SimpleNamespace

from scripts.usa_safari import REFERENCE_ROOT, build_prompts, get_mode, list_modes, parse_scene_brief, run_generation

_NEEDS_SOURCE_TYPES = {"controlnet", "img2img", "inpaint"}


# ── Чистые функции ────────────────────────────────────────────────────────────

def mode_options(modes):
    """Пары (подпись, id) для выпадающего списка: «1. Editorial VO — основные иллюстрации выпуска»."""
    options = []
    for m in modes:
        desc = m.get("description", "")
        short = desc.split(" — ", 1)[1] if " — " in desc else desc
        options.append((f"{m['label']} — {short}" if short else m["label"], m["id"]))
    return options


def uploads_needed(mode):
    """(нужен исходник, нужна маска) по типу режима."""
    return mode["mode_type"] in _NEEDS_SOURCE_TYPES, mode["mode_type"] == "inpaint"


def brief_to_fields(text, modes, ip_ref_dir):
    """Разбирает бриф и возвращает значения для полей интерфейса."""
    brief = parse_scene_brief(text)
    ids = [m["id"] for m in modes]
    mode_id = brief.get("mode_id") if brief.get("mode_id") in ids else ids[0]
    scene = brief.get("scene", "")
    if brief.get("character_desc"):
        scene = (scene + ", " + brief["character_desc"]).strip(", ")
    ref = brief.get("ip_ref_name")
    return {
        "mode_id": mode_id,
        "scene": scene,
        "with_character": bool(brief.get("with_character")),
        "use_ip": bool(brief.get("use_ip_adapter")),
        "ip_path": os.path.join(ip_ref_dir, ref) if ref else "",
    }


def describe_mode(mode):
    """Текст для «Показать параметры»: промпты и параметры режима."""
    lines = [f"─── {mode['label']}  [{mode['mode_type']}] ───", "", f"POSITIVE PREFIX:\n{mode['positive']}", ""]
    if mode.get("anatomy_addon"):
        lines += [f"ANATOMY ADD-ON:\n{mode['anatomy_addon']}", ""]
    lines.append(f"NEGATIVE:\n{mode['negative']}")
    if mode.get("anatomy_negative"):
        lines += ["", f"ANATOMY NEGATIVE:\n{mode['anatomy_negative']}"]
    dn, cn = mode.get("denoising"), mode.get("controlnet_type")
    kind = f"ControlNet: {cn}" if cn else (f"Denoising: {dn}" if dn else "text2img")
    lines += ["", "—" * 50,
              f"Steps: {mode.get('steps')}  |  CFG: {mode.get('cfg')}  |  {kind}  |  "
              f"Size: {mode.get('width')}×{mode.get('height')}"]
    return "\n".join(lines)


def save_uploaded(widget, prefix, upload_dir="/content"):
    """Сохраняет файл из виджета загрузки (форматы ipywidgets 7 и 8); None, если ничего не загружено."""
    val = widget.value
    if not val:
        return None
    if isinstance(val, (list, tuple)):
        item = val[0]
        name, data = item["name"], bytes(item["content"])
    else:
        name, item = next(iter(val.items()))
        data = bytes(item["content"])
    path = os.path.join(upload_dir, f"usa_safari_{prefix}_{name}")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


# ── Интерфейс ─────────────────────────────────────────────────────────────────

def build_ui(config, ip_ref_dir, upload_dir="/content", widgets=None, ipy_display=None, runner=None):
    """Строит и показывает интерфейс. widgets, ipy_display, runner можно подменить (тесты)."""
    if widgets is None:
        import ipywidgets as widgets
    if ipy_display is None:
        from IPython import display as ipy_display
    runner = runner or run_generation
    W, L = widgets, widgets.Layout
    modes = list_modes()

    def hidden(**kw):
        return L(display="none", **kw)

    brief_ta = W.Textarea(
        placeholder=("Вставь бриф от сценарного модуля:\n[режим]\nСцена: содержание\nПерсонаж: да / нет\n"
                     "Если да: силуэт / архетип\nИсходник: нет / есть (тип: stock / screenshot / video frame)\n"
                     "IP-Adapter: нет / да (ref: filename.jpg)"),
        layout=L(width="560px", height="120px"))
    parse_btn = W.Button(description="▶ Parse бриф", button_style="info", layout=L(width="140px"))
    parse_out = W.Output()
    brief_box = W.VBox([
        W.HTML("<b>📋 Бриф от сценарного модуля</b> (опционально — заполняет поля ниже автоматически):"),
        brief_ta, W.HBox([parse_btn, parse_out]), W.HTML("<hr style='margin:6px 0'>")])

    mode_dd = W.Dropdown(options=mode_options(modes), description="Режим:",
                         style={"description_width": "60px"}, layout=L(width="560px"))
    scene_ta = W.Textarea(placeholder="Опиши содержание сцены — только контент, стиль добавится автоматически...",
                          description="Сцена:", style={"description_width": "60px"},
                          layout=L(width="560px", height="90px"))

    src_upload = W.FileUpload(accept="image/*", multiple=False, description="Browse")
    src_path_w = W.Text(placeholder="или укажи путь: /content/image.jpg", layout=L(width="390px"))
    src_box = W.VBox([W.HTML("<b>📤 Base image</b> (стоковое фото / скриншот / кадр из видео):"),
                      W.HBox([src_upload, src_path_w])], layout=hidden(margin="4px 0 2px 0"))
    mask_upload = W.FileUpload(accept="image/*", multiple=False, description="Browse")
    mask_path_w = W.Text(placeholder="или укажи путь: /content/mask.jpg", layout=L(width="390px"))
    mask_box = W.VBox([W.HTML("<b>🎭 Mask</b> (белое = заменить, чёрное = сохранить):"),
                       W.HBox([mask_upload, mask_path_w])], layout=hidden(margin="2px 0 4px 0"))

    with_char_cb = W.Checkbox(value=False, description="С персонажем → добавить anatomy add-on", indent=False)
    ip_cb = W.Checkbox(value=False, description="IP-Adapter reference (консистентность лица в рамках расследования)",
                       indent=False)
    ip_upload = W.FileUpload(accept="image/*", multiple=False, description="📁 Reference")
    ip_path_w = W.Text(placeholder=f"или путь на Drive: {ip_ref_dir}/X.jpg", layout=L(width="480px"))
    ip_box = W.VBox([W.HBox([ip_upload, ip_path_w])], layout=hidden(margin="2px 0 4px 20px"))
    show_params_cb = W.Checkbox(value=False, description="Показать параметры (для ручной проверки)", indent=False)
    params_out = W.Output()

    gen_btn = W.Button(description="⚡ GENERATE", button_style="primary", layout=L(width="180px", height="40px"))
    status_out, result_out = W.Output(), W.Output()

    def update_uploads(mode_id):
        need_src, need_mask = uploads_needed(get_mode(mode_id))
        src_box.layout.display = "" if need_src else "none"
        mask_box.layout.display = "" if need_mask else "none"

    def render_params(change):
        with params_out:
            ipy_display.clear_output()
            if change["new"]:
                print(describe_mode(get_mode(mode_dd.value)))

    def on_parse(_):
        text = brief_ta.value.strip()
        with parse_out:
            ipy_display.clear_output()
            if not text:
                print("⚠️ Введи текст брифа")
                return
            try:
                f = brief_to_fields(text, modes, ip_ref_dir)
                mode_dd.value = f["mode_id"]
                scene_ta.value = f["scene"]
                with_char_cb.value = f["with_character"]
                if f["use_ip"]:
                    ip_cb.value = True
                    if f["ip_path"]:
                        ip_path_w.value = f["ip_path"]
                print(f"✅ Режим: {f['mode_id']} | Персонаж: {f['with_character']} | IP-Adapter: {f['use_ip']}")
            except Exception as e:
                print(f"❌ Ошибка парсинга: {e}")

    def on_generate(_):
        gen_btn.disabled = True
        with status_out:
            ipy_display.clear_output()
            print("🔄 Подготовка...")
        with result_out:
            ipy_display.clear_output()
        try:
            mode = get_mode(mode_dd.value)
            if not mode:
                raise ValueError(f"Режим '{mode_dd.value}' не найден")
            src = save_uploaded(src_upload, "src", upload_dir) or src_path_w.value.strip() or None
            mask = save_uploaded(mask_upload, "mask", upload_dir) or mask_path_w.value.strip() or None
            ip_ref = None
            if ip_cb.value:
                ip_ref = save_uploaded(ip_upload, "ip", upload_dir) or ip_path_w.value.strip() or None
            positive, negative = build_prompts(mode, scene_ta.value.strip(), with_char_cb.value)
            with status_out:
                ipy_display.clear_output()
                print(f"🔄 {mode['label']}...")
            saved = runner(mode, positive, negative, config, config["OUTPUT_DIR"],
                           src_path=src, mask_path=mask, ip_ref_path=ip_ref)
            with status_out:
                ipy_display.clear_output()
                print(f"✅ Готово: {saved}")
            with result_out:
                image_cls = getattr(ipy_display, "Image", None)
                if image_cls:
                    ipy_display.display(image_cls(saved, width=640))
        except Exception as e:
            with status_out:
                ipy_display.clear_output()
                print(f"❌ Ошибка: {e}")
                traceback.print_exc(file=sys.stdout)
        finally:
            gen_btn.disabled = False

    mode_dd.observe(lambda c: update_uploads(c["new"]), names="value")
    ip_cb.observe(lambda c: setattr(ip_box.layout, "display", "" if c["new"] else "none"), names="value")
    show_params_cb.observe(render_params, names="value")
    parse_btn.on_click(on_parse)
    gen_btn.on_click(on_generate)
    update_uploads(mode_dd.value)

    hr = lambda: W.HTML("<hr style='margin:6px 0'>")
    ipy_display.display(
        W.HTML("<h3 style='margin:8px 0'>🦁 USA Safari — Генератор</h3>"), brief_box, mode_dd, hr(), scene_ta,
        src_box, mask_box, hr(), with_char_cb, ip_cb, ip_box, show_params_cb, params_out, hr(),
        gen_btn, status_out, result_out)

    return SimpleNamespace(
        brief_ta=brief_ta, parse_btn=parse_btn, parse_out=parse_out, mode_dd=mode_dd, scene_ta=scene_ta,
        src_box=src_box, src_upload=src_upload, src_path_w=src_path_w,
        mask_box=mask_box, mask_upload=mask_upload, mask_path_w=mask_path_w,
        with_char_cb=with_char_cb, ip_cb=ip_cb, ip_box=ip_box, ip_upload=ip_upload, ip_path_w=ip_path_w,
        show_params_cb=show_params_cb, params_out=params_out,
        gen_btn=gen_btn, status_out=status_out, result_out=result_out)


def show_generator(config, ip_ref_dir=None, upload_dir="/content"):
    """Вызов из ячейки ноутбука. По умолчанию референсы персонажей: <корень референсов>/characters."""
    return build_ui(config, ip_ref_dir or str(REFERENCE_ROOT / "characters"), upload_dir)
