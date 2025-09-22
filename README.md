- `colab/` — основной ноутбук для Colab (с выбором модов: SD 1.5 / SDXL / SDXL Turbo).
- `prompts/` — рецепты генерации (JSON с prompt/negative/seed/steps/sampler/model и т.д.).
- `thumbnails/` — лёгкие превью (.jpg/.webp) к одноимённым JSON-рецептам.
- `scripts/` — утилиты (например, pull_models.py для скачивания весов из Hugging Face).
- `server/` — (на будущее) простой сервер-галерея.
- `models/`, `outputs/` — локальные кэши/артефакты, в git не идут.

> Тяжёлые веса (SD/SDXL/LoRA) в GitHub не храним. Держим ссылки на HF и скрипт скачивания.
test amend workflow Mon Sep 22 16:35:23 PDT 2025
