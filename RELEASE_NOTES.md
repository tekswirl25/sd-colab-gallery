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


## v0.1.17 (2025-09-25)

### ✨ Added

* add: SDXL Vintage Illustration Pro Turbo Gallery notebook ([220545f](https://github.com/tekswirl25/sd-colab-gallery/commit/220545f33f2840c21218426e426aa1aa107a32a9))


## v0.1.20 (2025-09-25)

### 🛠 Fixed

* fix: SDXL Vintage Illustration Pro Turbo Gallery notebook ([70416e3](https://github.com/tekswirl25/sd-colab-gallery/commit/70416e3656d379c61e390d05cc8c16b4b237fb16))


## v0.1.21 (2025-09-25)

### 🛠 Fixed

* fix: repo_init and server ([9639061](https://github.com/tekswirl25/sd-colab-gallery/commit/963906171e2e9caab39d39413d493fcf2795a44e))


## v0.1.22 (2025-09-25)

* added gradio server ([d020ac5](https://github.com/tekswirl25/sd-colab-gallery/commit/d020ac5bc1ef8502b9278eed306bfab48ee55100))


## v0.1.23 (2025-09-25)

* chore: sync .gitignore & .archiveignore from templates ([3094ae7](https://github.com/tekswirl25/sd-colab-gallery/commit/3094ae79ca3cd5da63c50d2bd608640850bb367f))


## v0.1.24 (2025-09-25)

### ✨ Added

* add: archive_commit.sh copied from git-hooks-utils ([7953366](https://github.com/tekswirl25/sd-colab-gallery/commit/795336639a9a7829afb82f9ac78a3e851f43aca4))


## v0.1.25 (2025-10-02)

### 🛠 Fixed

* fix: archive_commit.sh ([6ee9614](https://github.com/tekswirl25/sd-colab-gallery/commit/6ee9614309049ec58a2369da4363e71ef5eef2e2))


## v0.1.26 (2025-10-02)

### 🛠 Fixed

* fix: comment test in archive_commit.sh ([2b8e697](https://github.com/tekswirl25/sd-colab-gallery/commit/2b8e69766a9e1e0bddcdb371988db22edc44d166))


## v0.1.27 (2025-10-03)

### ✨ Added

* add: SDXL Vintage Illustration FULL Pro Turbo Gallery notebook ([c0cdf0d](https://github.com/tekswirl25/sd-colab-gallery/commit/c0cdf0d93019f2e26c8b24199df60ba753156a67))


## v0.1.28 (2025-10-03)

### 🛠 Fixed

* fix:gradio server: SDXL Vintage Illustration FULL Pro Turbo Gallery notebook ([b794ab0](https://github.com/tekswirl25/sd-colab-gallery/commit/b794ab02285a443cb16961314a5cda4547ab1f3b))


## v0.1.29 (2025-10-03)

### 🛠 Fixed

* fix:gradio server versionality ([5d90b8f](https://github.com/tekswirl25/sd-colab-gallery/commit/5d90b8f6c27cbf770a7f158a0ed177c93972c029))


## v0.1.30 (2025-10-03)

### 🛠 Fixed

* fix:gradio server versionality ([0147e75](https://github.com/tekswirl25/sd-colab-gallery/commit/0147e75b3255faaadf252e9ffde0198ad21ae195))


## v0.1.31 (2025-10-03)

### 🛠 Fixed

* fix:gradio server versionality ([e72e06d](https://github.com/tekswirl25/sd-colab-gallery/commit/e72e06dbd8ebd258aec1bf7e692405706c56baa5))


## v0.1.32 (2025-10-03)

### 🛠 Fixed

* fix:gradio server ([fcc031c](https://github.com/tekswirl25/sd-colab-gallery/commit/fcc031c0e72092ae3012f2e33963214e8850335d))


## v0.1.33 (2025-10-04)

### 🛠 Fixed

* fix:gradio server gallery ([016786c](https://github.com/tekswirl25/sd-colab-gallery/commit/016786c397e36603d5dfdb60867fafab89a87376))


## v0.1.34 (2025-10-04)

### 🛠 Fixed

* fix:gradio server gallery server_gradio.py mistypo ([dc9d408](https://github.com/tekswirl25/sd-colab-gallery/commit/dc9d408389fd795ec223979b31b3672d557cde10))


## v0.1.35 (2025-10-04)

### 🛠 Fixed

* fix:gradio server gallery server_gradio.py mistypo ([c47a2a2](https://github.com/tekswirl25/sd-colab-gallery/commit/c47a2a2a0d07a52f1a99d86ec2ddab4bed4a0e7d))


## v0.1.36 (2025-10-04)

### 🛠 Fixed

* fix:gradio server gallery server_gradio.py mistypo ([63afb30](https://github.com/tekswirl25/sd-colab-gallery/commit/63afb3073bcecf6f99517d46ad9f4f2131a36628))


## v0.1.37 (2025-10-04)

### 🛠 Fixed

* fix:gradio server gallery server_gradio.py mistypo ([bf5fe24](https://github.com/tekswirl25/sd-colab-gallery/commit/bf5fe24eb827d148573b8041d821458883e0c4a1))


## v0.1.38 (2025-10-04)

### 🛠 Fixed

* fix:gradio server gallery server_gradio.py added filter images by modules ([080f143](https://github.com/tekswirl25/sd-colab-gallery/commit/080f143812bc13d45cf9fa48117951a99eacd65a))


## v0.1.39 (2025-10-04)

### 🛠 Fixed

* fix:img2img and controlNet cells ([bbf1ad8](https://github.com/tekswirl25/sd-colab-gallery/commit/bbf1ad8700217447634c55ad14b0bf805a54402c))


## v0.1.40 (2025-10-04)

### 🛠 Fixed

* fix:save_image_and_meta method ([52998af](https://github.com/tekswirl25/sd-colab-gallery/commit/52998af895762a7fd1a496f773ed17a95ec254f2))


## v0.1.42 (2026-05-27)

* Update gallery scripts ([c29c4cb](https://github.com/tekswirl25/sd-colab-gallery/commit/c29c4cb63873521ef052fccc01277ac282c61b30))


## v0.1.43 (2026-05-27)

### 🛠 Fixed

* fix: Tips cell type code → markdown ([84148df](https://github.com/tekswirl25/sd-colab-gallery/commit/84148dfa34d6dd406ce8d837e8bdef2ec49e2622))


## v0.1.44 (2026-05-27)

### 🛠 Fixed

* fix: add missing build_style function to prompt_builder ([7735eae](https://github.com/tekswirl25/sd-colab-gallery/commit/7735eae0e6439ae4ff7ec23de45adb0e8090d11f))


## v0.1.45 (2026-05-27)

### 🛠 Fixed

* fix: use AutoPipeline for txt2img/img2img, variant-aware ControlNet ([a2e495e](https://github.com/tekswirl25/sd-colab-gallery/commit/a2e495e739f656866a1ea18cfc395a6d434a8b8d))


## v0.1.46 (2026-05-27)

### 🛠 Fixed

* fix: rename TURBO → SDXL_TURBO to match notebook dropdown ([e992d33](https://github.com/tekswirl25/sd-colab-gallery/commit/e992d3305f389ad02e3fd5da326dae6ee3ffb339))


## v0.1.47 (2026-05-27)

### 🛠 Fixed

* fix: add allowed_paths to Gradio launch for gallery file serving ([508477b](https://github.com/tekswirl25/sd-colab-gallery/commit/508477b88464f2784030feff686da32c0b79b69e))


## v0.1.48 (2026-05-27)

### 🛠 Fixed

* fix: add allowed_paths to Gradio launch for gallery file serving ([508477b](https://github.com/tekswirl25/sd-colab-gallery/commit/508477b88464f2784030feff686da32c0b79b69e))


## v0.1.49 (2026-05-27)

* Update gallery scripts ([f24a71e](https://github.com/tekswirl25/sd-colab-gallery/commit/f24a71ec259af8c511b8b2f269980e26f717d29d))


## v0.1.50 (2026-05-27)

### 🛠 Fixed

* fix: proper FileUpload widget with Browse + editable path + confirm ([163fc19](https://github.com/tekswirl25/sd-colab-gallery/commit/163fc1978824cc3ff6fe6ddee2330bd6231a508a))


## v0.1.51 (2026-05-27)

### 🛠 Fixed

* fix: remove Timer (perf), fix gallery format for Gradio 6, manual refresh only ([a24a1b5](https://github.com/tekswirl25/sd-colab-gallery/commit/a24a1b5e8300835cb50d494f919fe2792ed8d84c))


## v0.1.52 (2026-05-27)

### 🛠 Fixed

* fix: remove Timer (perf), fix gallery format for Gradio 6, manual refresh only ([a24a1b5](https://github.com/tekswirl25/sd-colab-gallery/commit/a24a1b5e8300835cb50d494f919fe2792ed8d84c))


## v0.1.53 (2026-05-27)

* Update gallery scripts ([6c80345](https://github.com/tekswirl25/sd-colab-gallery/commit/6c80345f2ab4db59bc89e6dab68052fb2b9f62a9))


## v0.1.54 (2026-05-27)

### 🛠 Fixed

* fix: remove Timer (perf), fix gallery format for Gradio 6, manual refresh only ([684ecd2](https://github.com/tekswirl25/sd-colab-gallery/commit/684ecd2ad878d061ef8df5d55ec1d619392007fc))


## v0.1.55 (2026-05-27)

### 🛠 Fixed

* fix: remove Timer (perf), fix gallery format for Gradio 6, manual refresh only ([684ecd2](https://github.com/tekswirl25/sd-colab-gallery/commit/684ecd2ad878d061ef8df5d55ec1d619392007fc))


## v0.1.56 (2026-05-27)

* Update gallery scripts ([ff7daec](https://github.com/tekswirl25/sd-colab-gallery/commit/ff7daec277d98498c7d8199a337ef6c8ead24794))


## v0.1.57 (2026-05-27)

### 🛠 Fixed

* fix: don't reset src_path/control_path in Img2Img/ControlNet cells ([c105dd2](https://github.com/tekswirl25/sd-colab-gallery/commit/c105dd276f7ed55b725ea16ecdf99a0fdac2aa3e))


## v0.1.58 (2026-05-27)

### 🛠 Fixed

* fix: fixed gallery height+rows for proper thumbnail grid ([e34fadd](https://github.com/tekswirl25/sd-colab-gallery/commit/e34faddf23dade97ccf460d8148890f9da0801d3))


## v0.1.59 (2026-05-27)

### 🛠 Fixed

* fix: fixed gallery height+rows for proper thumbnail grid ([e34fadd](https://github.com/tekswirl25/sd-colab-gallery/commit/e34faddf23dade97ccf460d8148890f9da0801d3))


## v0.1.60 (2026-05-28)

* Update gallery scripts ([f517eee](https://github.com/tekswirl25/sd-colab-gallery/commit/f517eee91e685c8e88c4c6785202f15e710fc570))

