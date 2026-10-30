# prompts

Проекты и стили для ноутбука. В ячейке «🎛 Проект и стиль» выбираешь `PROJECT` и `STYLE`, остальное подтягивается.

```
prompts/<проект>/project.yaml            имя, default_style, drive_output_dir (куда сохранять результаты на Drive)
prompts/<проект>/styles/<стиль>.yaml     стиль проекта
prompts/<проект>/characters/<имя>.yaml   промпт персонажа, seeds
prompts/_shared/styles/<стиль>.yaml      общие стили, доступны всем проектам
```

**Стиль** (`styles/*.yaml`): `label`, `base_style` и `color_tone` (имена из `presets/styles.json` и `presets/color_tones.json`), `positive` (добавка к промпту), `negative`, `params` (steps, cfg, width, height). Стиль проекта с тем же именем перекрывает общий.

**extends:** стиль может расширять другой (`extends: имя`): строки и скаляры заменяются, `params` сливаются по ключам.

**Промпт** собирается так: сцена, персонаж, base_style, color_tone, positive стиля.

Рецепты генераций (JSON с prompt, seed, steps, sampler, model) и превью лежат рядом по схеме `prompts/<model-id-safe>/<slug>.json` и `thumbnails/<model-id-safe>/<slug>.jpg`.
