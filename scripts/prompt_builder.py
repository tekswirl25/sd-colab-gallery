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


# ---------------------------------------------------------------------------
# USA Safari full presets
# ---------------------------------------------------------------------------

def get_full_style(name: str) -> dict | None:
    """
    Возвращает полный пресет стиля по имени из usa_safari_styles.json.

    Поля пресета:
      name, label, positive, positive_hands, negative,
      seed, width, height, steps, cfg, sampler

    Пример:
        preset = get_full_style("usa-safari-comics")
        # preset["positive"], preset["negative"], preset["seed"], ...

    Возвращает None, если имя не найдено.
    """
    presets = _load("usa_safari_styles.json")
    for p in presets:
        if p.get("name") == name:
            return p
    return None


def list_full_styles() -> list[str]:
    """Список доступных имён пресетов USA Safari."""
    presets = _load("usa_safari_styles.json")
    return [p["name"] for p in presets]
