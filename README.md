# SD Colab Gallery — USA Safari / Нескучная аналитика

Stable Diffusion на Google Colab для иллюстраций новостного канала **USA Safari**.
Стиль: editorial comic book — жирный линворк, плоские цвета, графика не фото.

---

## Структура проекта

- `colab/` — основной ноутбук (SD 1.5 / SDXL / SDXL Turbo) и `GPU_smoke_check.ipynb` — короткая проверка режимов на GPU после обновления (отчёт на Drive).
- `presets/` — JSON-конфиги стилей и режимов генерации.
  - `usa_safari_modes.json` — **7 рабочих режимов** (см. ниже).
  - `usa_safari_styles.json` — устаревший файл стилей (не использовать).
  - `color_tones.json`, `styles.json` — базовые пресеты.
- `scripts/` — Python-модули.
  - `usa_safari.py` — **главный модуль**: загрузка режимов, сборка промптов, роутинг генерации, IP-Adapter, логирование seeds.
  - `prompt_builder.py` — базовый построитель промптов.
  - `loaders.py` — фабрики пайплайнов SD (с кэшированием).
  - `config.py` — конфиги вариантов модели (SDXL / SD15 / Turbo).
  - `utils.py` — сохранение, thumbnails, memory management.
- `tests/` — тесты логики без GPU: `python -m unittest discover -s tests -t .`
- `prompts/`, `thumbnails/` — рецепты и превью (не в git при большом объёме).
- `models/`, `outputs/` — локальные кэши, в git не идут.

---

## 🦁 USA Safari — Генератор (ячейка в ноутбуке)

Один виджет вместо ручного заполнения промптов. Выбираешь режим → пишешь только содержание сцены → жмёшь GENERATE.

### 7 режимов

| # | Режим | Тип | Denoising | Назначение |
|---|-------|-----|-----------|------------|
| 1 | Editorial VO | text2img | — | Основные иллюстрации выпуска |
| 2 | Stock Ref → Comic | controlnet / openpose | — | Стоковое фото как поза (скелет) |
| 3 | News Screenshot | controlnet / canny | — | Скриншот новости → комикс (контуры) |
| 4 | Roto (Video Frame) | controlnet / canny | — | Кадр из видео → комикс |
| 5 | Inpaint — Anatomy | inpaint | 0.80 | Починить руки/пальцы |
| 6 | Inpaint — Signature | inpaint | 0.80 | Вставить/поправить подпись |
| 7 | Inpaint — Face | inpaint | 0.82 | Убрать узнаваемое лицо |

### Дополнительные опции виджета
- **С персонажем** — добавляет anatomy add-on к positive prompt.
- **IP-Adapter reference** — загружаешь thumbnail персонажа, он держит внешность во всех кадрах.
- **Показать параметры** — раскрывает все промпты для ручной правки перед генерацией.

---

## 🎨 Рекомендуемая модель и LoRA

### Checkpoint (хранить на Google Drive, ~2 GB)
**Dreamshaper 8** (SD 1.5) — лучший баланс для editorial comic illustration:
- Держит стиль комикса без перехода в аниме
- Хорошая детализация лиц и линворка
- Стабильна на шагах 25–35

Скачать: https://civitai.com/models/4384/dreamshaper (version 8)

Альтернатива если нужен более жёсткий графический стиль: **epiCRealism** + comic LoRA.

### LoRA (хранить на Google Drive, ~150 MB)
**Comics Lineart Style** — усиливает жирный линворк и уплощает цвета:
- Вес: 0.5–0.7 (выше → сильнее стилизация)

Скачать: https://civitai.com/models/13910

Добавить в positive prompt: `<lora:comics_lineart:0.6>`

### VAE (опционально, ~335 MB)
**vae-ft-mse-840000** — улучшает цвета и убирает серость:
- HuggingFace: `stabilityai/sd-vae-ft-mse`

---

## 📂 Google Drive — что хранить

```
MyDrive/
├── hf_cache/                    ← кэш HuggingFace (монтируется при старте)
│   └── models--...              ← веса скачиваются сюда автоматически
│
└── USA Safari Reference/        ← создаётся ячейкой Drive Reference Setup
    ├── characters/              ← thumbnails персонажей (512–768px JPEG)
    │   ├── official_canonical.jpg
    │   ├── investigator_canonical.jpg
    │   └── ...
    ├── style/                   ← стилевые референсы
    ├── seeds/
    │   └── seeds_log.txt        ← автологирование seeds при каждой генерации
    └── episodes/
        └── НА_YYYYMMDD/         ← финальные кадры выпуска
```

**Что класть на Drive для быстрого старта:**
- Checkpoint модели (Dreamshaper 8, ~2 GB)
- LoRA (Comics Lineart, ~150 MB)
- IP-Adapter веса (~1 GB, скачивается с HF автоматически при первом использовании)
- Thumbnails персонажей для IP-Adapter

Модели не скачиваются заново каждую сессию — Colab читает их с Drive напрямую.

---

## Рабочий процесс за одну сессию

1. Открыть Colab → запустить ячейки инициализации (Repo init → Drive → Config → Install deps)
2. Запустить **Drive Reference Setup** (один раз, создаёт папки)
3. Выбрать режим в **🦁 USA Safari — Генератор**
4. Писать только содержание сцены → GENERATE
5. Для следующих кадров с тем же персонажем — включить IP-Adapter + загрузить thumbnail

> Тяжёлые веса (SD/LoRA/IP-Adapter) в GitHub не храним. Держим на Google Drive.
