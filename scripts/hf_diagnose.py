# scripts/hf_diagnose.py
# Автор: genai_colab. Диагностика загрузки весов: какие файлы весов есть в репозитории
# модели (и какие из них pickle) и что лежит в кеше на месте упавшего файла
# (размер, начало, zip ли это, сравнение с размером на Hugging Face).

import os
import re
import zipfile

_WEIGHT_EXT = {".safetensors": "safetensors", ".bin": "bin", ".ckpt": "ckpt", ".pt": "pt", ".pth": "pth"}
_PICKLE = {"bin", "ckpt", "pt", "pth"}
# Google Drive не поддерживает символьные ссылки: кеш Hugging Face получает вместо ссылки
# маленький текстовый файл с путём вида ../../blobs/60/60dd...
_LINK_TEXT = re.compile(rb"^(\.\./)+blobs/\S+$")
_LINK_MAX_SIZE = 300


def is_symlink_text(path):
    """True, если обычный маленький файл содержит путь к blob (бывшая символьная ссылка)."""
    try:
        if os.path.islink(path) or os.path.getsize(path) > _LINK_MAX_SIZE:
            return False
        with open(path, "rb") as f:
            return bool(_LINK_TEXT.match(f.read(_LINK_MAX_SIZE + 1).strip()))
    except OSError:
        return False


def list_weight_files(repo, api):
    """Файлы весов репозитория: путь, размер, формат, pickle ли. api: huggingface_hub.HfApi."""
    try:
        info = api.model_info(repo, files_metadata=True)
    except Exception as e:  # сеть, нет репозитория, нет прав: отчёт важнее остановки
        return [{"error": f"{type(e).__name__}: {e}"}]
    rows = []
    for s in info.siblings:
        fmt = _WEIGHT_EXT.get(os.path.splitext(s.rfilename)[1].lower())
        if fmt:
            rows.append({"path": s.rfilename, "size": s.size, "format": fmt, "pickle": fmt in _PICKLE})
    return sorted(rows, key=lambda r: r["path"])


def format_weight_table(repo, rows):
    if rows and "error" in rows[0]:
        return f"{repo}: не удалось получить список файлов: {rows[0]['error']}"
    has_safe = any(r["format"] == "safetensors" for r in rows)
    lines = [f"{repo}: safetensors: {'да' if has_safe else 'нет'}"]
    for r in rows:
        size = f"{r['size'] / 1e9:.2f} ГБ" if r["size"] else "?"
        lines.append(f"   {r['path']}  {size}  {'pickle' if r['pickle'] else 'безопасный'}")
    return "\n".join(lines)


def inspect_local_file(path):
    """Размер, первые байты, zip ли, не указатель ли git-lfs. Символьные ссылки разворачиваются."""
    if not os.path.exists(path):
        return {"path": path, "error": "файла нет"}
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        head = f.read(64)
    return {
        "path": path,
        "size": size,
        "head_hex": head[:16].hex(),
        "is_zip": zipfile.is_zipfile(path) if size else False,
        "lfs_pointer": head.startswith(b"version https://git-lfs"),
        "symlink_text": is_symlink_text(path),
    }


def verdict(info, remote_size=None):
    """Одна строка вывода о файле."""
    if info.get("error"):
        return info["error"]
    if info["size"] == 0:
        return "файл пустой"
    if info.get("symlink_text"):
        return "это не файл, а текстовая замена символьной ссылки: Google Drive не поддерживает ссылки, кеш Hugging Face на Drive сломан"
    if info["lfs_pointer"]:
        return "это указатель git-lfs, а не веса (скачалось не до конца)"
    if remote_size and info["size"] < remote_size:
        return f"файл обрезан: {info['size']} из {remote_size} байт"
    if not info["is_zip"]:
        same = " (размер совпадает с Hugging Face)" if remote_size and info["size"] == remote_size else ""
        return f"это не zip-архив PyTorch{same}: старый формат или повреждение"
    if remote_size and info["size"] == remote_size:
        return "размер совпадает с Hugging Face, формат zip: файл целый"
    return "формат zip, сравнить размер с Hugging Face не удалось"
