import json
from pathlib import Path

PRESETS_DIR = Path("presets")

def _load(file: str):
    path = PRESETS_DIR / file
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_prompt(text: str, style: str = None, tone: str = None) -> str:
    """Собирает финальный промпт из текста + выбранного стиля и тона."""
    styles = {s["name"]: s["prompt"] for s in _load("styles.json")}
    tones = {t["name"]: t["prompt"] for t in _load("color_tones.json")}

    parts = [text]
    if style and style in styles:
        parts.append(styles[style])
    if tone and tone in tones:
        parts.append(tones[tone])

    return ", ".join(parts)
