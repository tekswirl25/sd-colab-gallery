# scripts/hf_cache_check.py
# Автор: genai_colab. Проверка кеша моделей Hugging Face (например на Google Drive):
# пустые и недокачанные файлы ломают загрузку модели (IndexError: pop from empty list
# внутри torch.load). Находит такие файлы, называет затронутые модели, по просьбе
# удаляет папки этих моделей, чтобы они скачались заново.

import os
import shutil

_MODEL_PREFIX = "models--"


def find_broken_files(cache_dir):
    """{'empty': [пути файлов нулевого размера], 'incomplete': [пути *.incomplete]}."""
    found = {"empty": [], "incomplete": []}
    if not os.path.isdir(cache_dir):
        return found
    for root, dirs, files in os.walk(cache_dir):
        dirs[:] = [d for d in dirs if d != ".locks"]  # служебные файлы блокировок пустые всегда
        for name in files:
            path = os.path.join(root, name)
            if name.endswith(".incomplete"):
                found["incomplete"].append(path)
                continue
            try:
                size = os.stat(path).st_size  # по ссылке: смотрим на реальный файл
            except OSError:
                size = 0  # ссылка в никуда: файл модели отсутствует
            if size == 0:
                found["empty"].append(path)
    found["empty"].sort()
    found["incomplete"].sort()
    return found


def affected_models(found, cache_dir):
    names = set()
    for path in found["empty"] + found["incomplete"]:
        first = os.path.relpath(path, cache_dir).split(os.sep)[0]
        if first.startswith(_MODEL_PREFIX):
            names.add(first)
    return sorted(names)


def remove_models(names, cache_dir):
    """Удаляет папки моделей из кеша. Принимает только имена вида models--org--name."""
    for name in names:
        if not name.startswith(_MODEL_PREFIX) or "/" in name or "\\" in name or ".." in name:
            raise ValueError(f"не папка модели в кеше: {name!r}")
    removed = []
    for name in names:
        path = os.path.join(cache_dir, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
            removed.append(name)
    return removed


def format_report(found, cache_dir, deleted, max_paths=10):
    if not found["empty"] and not found["incomplete"]:
        return f"✅ В кеше {cache_dir} пустых и недокачанных файлов нет."
    models = affected_models(found, cache_dir)
    lines = [f"⚠️ В кеше {cache_dir}: пустых файлов {len(found['empty'])}, недокачанных {len(found['incomplete'])}."]
    lines += [f"   затронута модель: {m}" for m in models]
    outside = [p for p in found["empty"] + found["incomplete"]
               if not os.path.relpath(p, cache_dir).split(os.sep)[0].startswith(_MODEL_PREFIX)]
    if outside:
        lines.append(f"   вне папок моделей ({len(outside)}):")
        lines += [f"      {os.path.relpath(p, cache_dir)}" for p in outside[:max_paths]]
        if len(outside) > max_paths:
            lines.append(f"      и ещё {len(outside) - max_paths}")
    if not models:
        lines.append("✅ Файлы моделей целы, модели не затронуты: это служебные файлы кеша, удалять нечего.")
    elif deleted:
        lines.append("🗑️ Папки этих моделей удалены, при следующем запуске они скачаются заново.")
    else:
        lines.append("Чтобы скачать их заново, поставь DELETE_BROKEN = True и запусти ячейку ещё раз.")
    return "\n".join(lines)
