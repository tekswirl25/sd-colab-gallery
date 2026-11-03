# scripts/gallery_data.py
# Автор: genai_colab. Данные для галереи Gradio без самого Gradio (тесты без него):
# список картинок режима (новые первыми), подписи с seed, сведения для копирования и скачивания.

import base64
import html
import io
import json
import os
import re

from PIL import Image

_IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")
_STAMP = re.compile(r"\d{8}_\d{6}")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.\-]+$")


def _meta(image_path):
    """Метаданные картинки из <имя>.png.json; пусто, если файла нет или он повреждён."""
    try:
        with open(image_path + ".json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def list_items(mode_dir):
    """Картинки папки режима, новые первыми: {image, thumb, name, meta, seed, caption}."""
    if not os.path.isdir(mode_dir):
        return []
    thumb_dir = os.path.join(os.path.dirname(mode_dir.rstrip(os.sep)), "thumbnails", os.path.basename(mode_dir.rstrip(os.sep)))
    items = []
    for fname in sorted(os.listdir(mode_dir), reverse=True):
        base, ext = os.path.splitext(fname)
        if ext.lower() not in _IMAGE_EXT or fname.startswith("."):
            continue
        image = os.path.join(mode_dir, fname)
        thumb = os.path.join(thumb_dir, base + ".jpg")
        meta = _meta(image)
        seed = meta.get("seed")
        stamp = _STAMP.search(base)
        caption = f"seed {seed} · {stamp.group(0) if stamp else base}" if seed is not None else base
        items.append({"image": image, "thumb": thumb if os.path.exists(thumb) else None, "name": base,
                      "meta": meta, "seed": seed, "caption": caption})
    return items


def item_details(item):
    """Текст для полей «Seed», «Prompt», «Параметры» и файл для скачивания."""
    if not item:
        return {"seed": "", "prompt": "", "params": "", "file": None}
    meta = item["meta"]
    return {
        "seed": "" if item["seed"] is None else str(item["seed"]),
        "prompt": str(meta.get("prompt", "")),
        "params": json.dumps(meta, ensure_ascii=False, indent=2) if meta else "",
        "file": item["image"],
    }


def parse_link_query(query, modes):
    """Параметры ссылки из ноутбука (?mode=text2img&img=имя). None, если что-то не так или имя небезопасно."""
    if not query:
        return None
    mode, name = query.get("mode"), query.get("img")
    if mode not in modes or not name or not _SAFE_NAME.match(name):
        return None
    return mode, name


def find_item(items, name):
    """Индекс картинки по имени (с расширением или без); None, если такой нет."""
    base = os.path.splitext(name)[0] if os.path.splitext(name)[1].lower() in _IMAGE_EXT else name
    for i, item in enumerate(items):
        if item["name"] == base:
            return i
    return None


# ───────────── Просмотр без файлового сервера Gradio ─────────────
# Gallery, File и Image отдают картинки через файловый сервер Gradio, в Colab они приходят битыми.
# Поэтому картинки встраиваются в страницу (data URI), а удаление идёт напрямую по файлам.

_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


def _jpeg_uri(path, side):
    """JPEG data URI картинки, уменьшенной так, что большая сторона не больше side; оригинал не меняется."""
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((side, side))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def grid_html(items, limit=48, thumb_side=256):
    """Сетка миниатюр с подписями, новые первыми; показаны последние limit, про остальные сказано."""
    if not items:
        return '<div style="font:14px sans-serif;color:#666">Картинок пока нет.</div>'
    cards = []
    for number, item in enumerate(items[:limit], 1):
        try:
            uri = _jpeg_uri(item["thumb"] or item["image"], thumb_side)
        except Exception:
            continue
        cards.append('<div style="width:%dpx;font:12px sans-serif"><img src="%s" style="width:100%%;border-radius:4px">'
                     '<div>%d. %s</div></div>' % (thumb_side, uri, number, html.escape(item["caption"])))
    rest = len(items) - limit
    note = f'<div style="font:12px sans-serif;color:#666">…и ещё {rest} (выбери кадр в списке)</div>' if rest > 0 else ""
    return '<div style="display:flex;flex-wrap:wrap;gap:8px">' + "".join(cards) + "</div>" + note


def view_html(item, preview_side=1024):
    """Крупный просмотр кадра и ссылка на скачивание оригинала; пусто, если кадра нет."""
    if not item:
        return ""
    try:
        preview = _jpeg_uri(item["image"], preview_side)
        with open(item["image"], "rb") as f:
            raw = base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return '<div style="font:14px sans-serif;color:#a00">Файл не удалось прочитать.</div>'
    fname = os.path.basename(item["image"])
    mime = _MIME.get(os.path.splitext(fname)[1].lower(), "application/octet-stream")
    return ('<div style="font:14px sans-serif"><img src="%s" style="max-width:100%%;border-radius:4px">'
            '<div style="margin-top:6px"><a download="%s" href="data:%s;base64,%s" role="button" '
            'style="display:inline-block;padding:6px 14px;border-radius:6px;background:#1a73e8;color:#fff;'
            'text-decoration:none">⬇ Скачать оригинал</a> %s</div></div>'
            % (preview, html.escape(fname, quote=True), mime, raw, html.escape(fname)))


def choices(items):
    """Варианты для списка выбора: (подпись, имя), новые первыми."""
    return [(item["caption"], item["name"]) for item in items]


def tick_choices(items):
    """Варианты для отметки нескольких кадров: «номер. подпись» (номер тот же, что на миниатюре в сетке) и имя."""
    return [(f"{number}. {item['caption']}", item["name"]) for number, item in enumerate(items, 1)]


def neighbor(items, name, step):
    """Имя соседнего кадра (step +1 или -1) по кругу; без выбора или с неизвестным именем первый кадр; None, если пусто."""
    if not items:
        return None
    index = find_item(items, name) if name else None
    if index is None:
        return items[0]["name"]
    return items[(index + step) % len(items)]["name"]


def _remove(item):
    """Удаляет картинку, её метаданные и миниатюру; True, если картинка удалена."""
    removed = False
    for path in (item["image"], item["image"] + ".json", item.get("thumb")):
        if path and os.path.exists(path):
            try:
                os.remove(path)
                removed = removed or path == item["image"]
            except OSError:
                pass
    return removed


def delete_one(items, name):
    """Удаляет один кадр списка items по имени. Имя ищется только среди известных кадров: путей оно не задаёт."""
    index = find_item(items, name) if name and _SAFE_NAME.match(name) else None
    return index is not None and _remove(items[index])


def delete_all(items):
    """Удаляет все кадры списка; возвращает сколько удалено."""
    return sum(1 for item in items if _remove(item))


def delete_many(items, names):
    """Удаляет отмеченные кадры списка items по именам; неизвестные и небезопасные имена пропускаются. Возвращает сколько удалено."""
    return sum(1 for name in dict.fromkeys(names or []) if delete_one(items, name))
