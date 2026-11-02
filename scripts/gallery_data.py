# scripts/gallery_data.py
# Автор: genai_colab. Данные для галереи Gradio без самого Gradio (тесты без него):
# список картинок режима (новые первыми), подписи с seed, сведения для копирования и скачивания.

import json
import os
import re

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
