# scripts/style_presets.py
# Автор: genai_colab. Проекты и стили: prompts/<проект>/{project.yaml, styles/, characters/}.
# Общие стили лежат в prompts/_shared/styles/ и доступны каждому проекту; стиль проекта
# с тем же именем перекрывает общий. Стиль может расширять другой (extends):
# скаляры и строки заменяются, params сливаются по ключам.

import json
import os

import yaml

SHARED = "_shared"


def _read_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _names(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-5] for f in os.listdir(folder) if f.endswith(".yaml") and not f.startswith("fldr_"))


def list_projects(root="prompts"):
    if not os.path.isdir(root):
        return []
    return sorted(
        d for d in os.listdir(root)
        if not d.startswith(("_", ".")) and os.path.isfile(os.path.join(root, d, "project.yaml"))
    )


def load_project(project, root="prompts"):
    path = os.path.join(root, project, "project.yaml")
    if not os.path.isfile(path):
        raise ValueError(f"проект {project!r} не найден; есть: {', '.join(list_projects(root))}")
    return _read_yaml(path)


def list_styles(project, root="prompts"):
    own = _names(os.path.join(root, project, "styles"))
    shared = _names(os.path.join(root, SHARED, "styles"))
    return sorted(set(own) | set(shared))


def list_characters(project, root="prompts"):
    return _names(os.path.join(root, project, "characters"))


def load_character(project, name, root="prompts"):
    path = os.path.join(root, project, "characters", f"{name}.yaml")
    if not os.path.isfile(path):
        raise ValueError(f"персонаж {name!r} не найден в проекте {project!r}; есть: {', '.join(list_characters(project, root))}")
    return _read_yaml(path)


def _style_path(project, name, root):
    for folder in (os.path.join(root, project, "styles"), os.path.join(root, SHARED, "styles")):
        path = os.path.join(folder, f"{name}.yaml")
        if os.path.isfile(path):
            return path
    return None


def load_style(project, style, root="prompts", _seen=()):
    """Стиль со всеми унаследованными полями (поле extends убирается)."""
    if style in _seen:
        raise ValueError(f"цикл в extends: {' -> '.join(_seen + (style,))}")
    path = _style_path(project, style, root)
    if path is None:
        raise ValueError(f"стиль {style!r} не найден для проекта {project!r}; есть: {', '.join(list_styles(project, root))}")
    data = _read_yaml(path)
    parent = data.pop("extends", None)
    if not parent:
        return data
    try:
        base = load_style(project, parent, root, _seen + (style,))
    except ValueError as e:
        if "не найден" in str(e):
            raise ValueError(f"стиль {style!r} расширяет {parent!r}, которого нет") from e
        raise
    merged = dict(base)
    for key, val in data.items():
        if key == "params":
            merged["params"] = {**base.get("params", {}), **(val or {})}
        else:
            merged[key] = val
    return merged


def _lookup(presets_dir, file, name, kind):
    path = os.path.join(presets_dir, file)
    items = json.load(open(path, encoding="utf-8")) if os.path.isfile(path) else []
    for item in items:
        if item["name"] == name:
            return item["prompt"]
    raise ValueError(f"{kind} {name!r} нет в {file}")


def resolve(project, style=None, character=None, root="prompts", presets_dir="presets"):
    """
    Всё, что ноутбуку нужно от выбранного проекта и стиля: имена base_style и color_tone,
    extra (промпт персонажа + positive стиля), negative, params, папка вывода на Drive.
    Имена base_style и color_tone проверяются по presets/*.json.
    """
    proj = load_project(project, root)
    style = style or proj.get("default_style")
    if not style:
        raise ValueError(f"у проекта {project!r} не задан default_style, укажи стиль явно")
    st = load_style(project, style, root)
    if st.get("base_style"):
        _lookup(presets_dir, "styles.json", st["base_style"], "base_style")
    if st.get("color_tone"):
        _lookup(presets_dir, "color_tones.json", st["color_tone"], "color_tone")
    char_prompt = load_character(project, character, root).get("prompt", "") if character else ""
    extra = ", ".join(x.strip() for x in (char_prompt, st.get("positive", "")) if x and x.strip())
    return {
        "project": project,
        "style": style,
        "base_style": st.get("base_style"),
        "color_tone": st.get("color_tone"),
        "extra": extra,
        "negative": (st.get("negative") or "").strip(),
        "params": dict(st.get("params", {})),
        "drive_output_dir": proj.get("drive_output_dir"),
    }


def compose(project, style, scene, character=None, root="prompts", presets_dir="presets"):
    """Полные positive и negative промпты (порядок как в ноутбуке: сцена, стиль, тон, персонаж, добавка стиля)."""
    r = resolve(project, style, character, root, presets_dir)
    parts = [scene]
    if r["base_style"]:
        parts.append(_lookup(presets_dir, "styles.json", r["base_style"], "base_style"))
    if r["color_tone"]:
        parts.append(_lookup(presets_dir, "color_tones.json", r["color_tone"], "color_tone"))
    parts.append(r["extra"])
    return {
        "project": r["project"],
        "style": r["style"],
        "positive": ", ".join(p.strip() for p in parts if p and p.strip()),
        "negative": r["negative"],
        "params": r["params"],
        "drive_output_dir": r["drive_output_dir"],
    }
