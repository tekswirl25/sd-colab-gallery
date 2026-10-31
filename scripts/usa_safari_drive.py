# scripts/usa_safari_drive.py
# Автор: genai_colab. Создаёт структуру папок «USA Safari Reference» на Google Drive
# (раньше этот код лежал в ячейке ноутбука). Безопасно запускать повторно: ничего не затирает.

import os

from scripts.usa_safari import REFERENCE_ROOT

SUBFOLDERS = ("characters", "style", "seeds", "episodes")
_SEEDS_HEADER = (
    "# USA Safari — Seeds Log\n"
    "# Формат: [timestamp] seed=N | mode=... | file=...\n"
    "#          prompt: первые 120 символов\n\n"
)


def default_root():
    return str(REFERENCE_ROOT)


def setup_drive_reference(root=None):
    """Создаёт папки и seeds_log.txt, если их нет. Возвращает, что где лежит."""
    root = root or default_root()
    dirs = []
    for name in SUBFOLDERS:
        path = os.path.join(root, name)
        os.makedirs(path, exist_ok=True)
        dirs.append(path)
    log = os.path.join(root, "seeds", "seeds_log.txt")
    created = not os.path.exists(log)
    if created:
        with open(log, "w", encoding="utf-8") as f:
            f.write(_SEEDS_HEADER)
    return {"root": root, "dirs": dirs, "seeds_log": log, "seeds_log_created": created}


def format_setup(result):
    lines = [f"✅ {d}" for d in result["dirs"]]
    lines.append(f"✅ {result['seeds_log']} " + ("создан" if result["seeds_log_created"] else "уже существует"))
    lines += ["", "Сохраняй canonical thumbnails персонажей в characters/ (512–768px JPEG)",
              "Стилевые референсы — в style/", "Финальные кадры выпуска — в episodes/НА_YYYYMMDD/"]
    return "\n".join(lines)
