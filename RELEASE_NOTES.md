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
