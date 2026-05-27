import json
from pathlib import Path

PRESETS_DIR = Path("presets")

def _load(file: str):
    path = PRESETS_DIR / file
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_style(style: str = None, tone: str = None) -> str:
    """Возвращает суффикс стиля+тона без пользовательского текста."""
    styles = {s["name"]: s["prompt"] for s in _load("styles.json")}
    tones = {t["name"]: t["prompt"] for t in _load("color_tones.json")}

    parts = []
    if style and style in styles:
        parts.append(styles[style])
    if tone and tone in tones:
        parts.append(tones[tone])

    return ", ".join(parts)


def build_prompt(text: str, style: str = None, tone: str = None) -> str:
    """Собирает финальный промпт из текста + выбранного стиля и тона."""
    suffix = build_style(style=style, tone=tone)
    parts = [text]
    if suffix:
        parts.append(suffix)
    return ", ".join(parts)
