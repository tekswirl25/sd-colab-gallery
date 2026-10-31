# scripts/notebook_uploads.py
# Автор: genai_colab. Ячейки загрузки файлов основного ноутбука (раньше четыре копии по 42 строки
# в самом ноутбуке). Подтверждённые пути хранятся здесь: ячейки генерации берут их по умолчанию.

import os

from scripts.usa_safari_ui import save_uploaded

PATHS = {}  # вид загрузки -> подтверждённый путь

KINDS = {
    "img2img": ("src_path", "📌 1) Browse → выбери файл   2) Use path → → только потом запускай следующую ячейку"),
    "controlnet": ("control_path", "📌 1) Browse → выбери файл   2) Use path → → только потом запускай следующую ячейку"),
    "inpaint_image": ("inpaint_src_path", "📌 1) Browse image   2) Use path ➜   3) Run mask upload cell"),
    "inpaint_mask": ("inpaint_mask_path", "📌 WHITE = replace, BLACK = keep. 1) Browse mask   2) Use path ➜"),
}


def get_path(kind):
    return PATHS.get(kind)


def show_upload(kind, upload_dir="/content", widgets=None, ipy_display=None):
    """Показывает виджет загрузки для вида kind; возвращает его элементы (для тестов)."""
    if kind not in KINDS:
        raise ValueError(f"неизвестный вид загрузки {kind!r}; есть: {', '.join(KINDS)}")
    if widgets is None:
        import ipywidgets as widgets
    if ipy_display is None:
        from IPython import display as ipy_display
    label, hint = KINDS[kind]
    W, L = widgets, widgets.Layout

    upload_btn = W.FileUpload(accept="image/*", multiple=False, description="📁 Browse", layout=L(width="140px"))
    path_box = W.Text(value="", placeholder="/content/image.jpg", description="Path:", layout=L(width="460px"))
    confirm_btn = W.Button(description="Use path ➜", button_style="primary", layout=L(width="140px"))
    status_out = W.Output()

    def on_upload(change):
        if not upload_btn.value:
            return
        path = save_uploaded(upload_btn, kind, upload_dir)
        # прежнее имя файла без префикса: как в старых ячейках
        val = upload_btn.value
        name = val[0]["name"] if isinstance(val, (list, tuple)) else next(iter(val))
        dest = os.path.join(upload_dir, name)
        if path != dest:
            os.replace(path, dest)
        path_box.value = dest
        with status_out:
            ipy_display.clear_output()
            print(f"✅ {name}  ({os.path.getsize(dest) / 1024:.1f} KB)  →  {dest}")

    def on_confirm(_):
        path = path_box.value
        with status_out:
            ipy_display.clear_output()
            if path and os.path.exists(path):
                PATHS[kind] = path
                print(f"✅ {label} = {path!r}")
            else:
                print(f"⚠️ Файл не найден: {path!r}")

    upload_btn.observe(on_upload, names="value")
    confirm_btn.on_click(on_confirm)
    print(hint)
    ipy_display.display(W.VBox([W.HBox([upload_btn, confirm_btn]), path_box, status_out]))
    from types import SimpleNamespace
    return SimpleNamespace(upload_btn=upload_btn, path_box=path_box, confirm_btn=confirm_btn, status_out=status_out)
