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

