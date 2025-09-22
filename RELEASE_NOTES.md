# 📒 Release Notes — SDXL Gallery Colab

## v0.1.0 (2025-09-21)
Initial modularization and cleanup of the Colab notebook.  
Base structure ready for SDXL / Turbo / SD1.5 with Flask gallery.

### ✅ Added
- Clean Colab structure:
  1. 🎨 Header
  2. ✅ Tips
  3. 🔧 Config init
  4. 📦 Server (Flask gallery + logs)
  5. 📦 Install dependencies
  6. 🔁 Imports & utils
  7. 🧠 Model loaders
  8. 🎨 Style base & prompt builder
  9. 🖼 Text2Img
  10. 🖼 Img2Img
  11. 🧭 ControlNet (Canny)
  12. ⬆️ Upscale x4

- Scripts:
  - `config.py` — CONFIG, VARIANTS, VARIANT_MODELS, DEFAULTS
  - `utils.py` — helpers (ts_now, save_image_and_meta, list_images…)
  - `loaders.py` — get_txt2img_pipe, get_img2img_pipe, get_controlnet_pipe, get_upscale_pipe
  - `logger.py` — log_info, LOG_FILE
  - `gallery_manager.py` — Flask gallery + JSON metadata + /logs

### 🔄 Changed
- Removed duplicated code from Colab → moved to `scripts/`
- Centralized model IDs in `config.py`
- Standardized JSON metadata saving
- Gallery starts at notebook launch, logs viewable at `/logs`

### 📝 TODO
- [ ] Add dropdown for `COLOR_TONE_PRESETS` in Colab
- [ ] Expand ControlNet support (depth, openpose)
- [ ] Draft mode (low-res fast preview)
- [ ] Auto-zip outputs after each run
- [ ] Unit tests for `utils` and `loaders`

## v0.1.1 (2025-09-21)

### 🛠 Fixed

* fix: dummy commit for testing ([8f476af](https://github.com/tekswirl25/sd-colab-gallery/commit/8f476afba85268cecb899907b8b61f6813bd147b))


## v0.1.2 (2025-09-21)

### ✨ Added

* add: release automation script and GitHub Actions workflow ([25cf883](https://github.com/tekswirl25/sd-colab-gallery/commit/25cf8839d3a34761c33079b2eae67e58de58cd61))


## v0.1.3 (2025-09-21)

### 🛠 Fixed

* fix: grant permissions for GitHub Actions to update release notes ([1fc2bb6](https://github.com/tekswirl25/sd-colab-gallery/commit/1fc2bb6d3ce5f52a78768b7dcfecde983bd67b68))


## v0.1.4 (2025-09-21)

### 🛠 Fixed

* fix: update .gitignore to ignore .DS_Store ([5d41716](https://github.com/tekswirl25/sd-colab-gallery/commit/5d417168eb7a427325c9c8dc0a976b00ef336f9d))


## v0.1.5 (2025-09-21)

* add VARIANT_MODELS to config.py ([a960c0f](https://github.com/tekswirl25/sd-colab-gallery/commit/a960c0fc233794dfb1b84ad6aa3180e29b0fbb11))


## v0.1.6 (2025-09-22)

* chore: set RELEASE_NOTES.md to always prefer remote version ([04d42c0](https://github.com/tekswirl25/sd-colab-gallery/commit/04d42c0a65b31d06cf95a9606556a3f995bb2632))


## v0.1.7 (2025-09-22)

### 🛠 Fixed

* fix: apply all modified files ([fa48705](https://github.com/tekswirl25/sd-colab-gallery/commit/fa4870525f0d83c57d3edbd0aa1c4f997de62417))


## v0.1.8 (2025-09-22)

### ✨ Added

* add: SDXL Vintage Illustration FULL Pro Turbo Gallery notebook ([9ab11a7](https://github.com/tekswirl25/sd-colab-gallery/commit/9ab11a7896208d181c6b7d4171ff0b901fca4323))


## v0.1.10 (2025-09-22)

### 🔄 Changed

* change: update version, release notes and add SDXL Vintage Illustration notebook ([a20add9](https://github.com/tekswirl25/sd-colab-gallery/commit/a20add9c5aec98719a8f084dbb0f60b85f43b080))


## v0.1.11 (2025-09-22)

### 🔄 Changed

* change: update .gitattributes ([c8d162a](https://github.com/tekswirl25/sd-colab-gallery/commit/c8d162ae3b1eec2f0f03ac5fcea4f2e1a5787efb))


## v0.1.12 (2025-09-22)

### 🔄 Changed

* change: update version, release notes and add SDXL Vintage Illustration notebook ([c7f9ba9](https://github.com/tekswirl25/sd-colab-gallery/commit/c7f9ba9f8882e70c9560548c30d68ad44be842fb))


## v0.1.13 (2025-09-22)

* Merge branch 'main' of github.com:tekswirl25/sd-colab-gallery ([e8ec468](https://github.com/tekswirl25/sd-colab-gallery/commit/e8ec468d8b7f7645c87c66a36bdb9999c0812022))


## v0.1.14 (2025-09-22)

* chore: update release notes [skip ci] ([07f4907](https://github.com/tekswirl25/sd-colab-gallery/commit/07f4907fb2822c1d31d5b6490765e6e4fcfbddf5))


## v0.1.15 (2025-09-22)

* test: trigger release notes amend ([c2c657c](https://github.com/tekswirl25/sd-colab-gallery/commit/c2c657cd1ff4dd7028065dcfe088fbe5cfff3384))

