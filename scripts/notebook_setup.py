# scripts/notebook_setup.py
# Автор: genai_colab. Подготовка основного ноутбука одним вызовом: Drive и кеш моделей, установка
# зависимостей, конфиг, утилиты и загрузчики. Раньше это были семь ячеек с кодом: то, что всегда нужно
# вместе, теперь грузится вместе. Каждый шаг можно подменить (тесты без Colab и сети).

import os
import subprocess
import sys


def _pip(args):
    subprocess.check_call([sys.executable, "-m", "pip", *args])


def install_dependencies(mode, run=None):
    """Устанавливает зависимости. xformers и controlnet_aux необязательны: сбой только предупреждает."""
    run = run or (lambda cmd: _pip(cmd[3:]))
    pip = [sys.executable, "-m", "pip"]
    run(pip + ["install", "--quiet", "torch", "torchvision", "torchaudio"])
    run(pip + ["install", "--quiet", "--upgrade", "diffusers", "transformers", "accelerate", "safetensors", "gradio"])
    try:
        run(pip + ["install", "--quiet", "xformers"])
        print("✅ xformers installed")
    except Exception as e:
        print(f"⚠️ xformers not installed (optional): {e}")
    run(pip + ["install", "--quiet", "opencv-python-headless", "pillow", "ipywidgets", "packaging", "pyyaml"])
    print(f"✅ Dependencies installed for MODE={mode}")
    try:
        run(pip + ["install", "--quiet", "controlnet_aux"])
    except Exception:
        print("⚠️ controlnet_aux не установлен — OpenPose будет заменён на Canny")


def mount_drive_and_cache(mount_point, hf_cache_dir, mount=None):
    """
    Монтирует Google Drive (для результатов и отчётов) и направляет кеш Hugging Face в hf_cache_dir.
    Кеш на Drive держать нельзя: Drive не поддерживает символьные ссылки, на которых он стоит.
    """
    if os.path.abspath(hf_cache_dir).startswith(os.path.abspath(mount_point) + os.sep):
        raise ValueError(f"Кеш моделей нельзя держать на Drive ({hf_cache_dir}): Drive ломает символьные ссылки "
                         "кеша Hugging Face. Укажи локальную папку, например /content/hf_cache.")
    if mount is None:
        from google.colab import drive
        mount = drive.mount
    mount(mount_point)
    os.makedirs(hf_cache_dir, exist_ok=True)
    os.environ["HF_HOME"] = hf_cache_dir
    os.environ["HUGGINGFACE_HUB_CACHE"] = hf_cache_dir
    print(f"✅ Drive mounted at {mount_point}")
    print(f"✅ HF_HOME = {hf_cache_dir}")
    try:
        du = subprocess.run(["du", "-sh", hf_cache_dir], capture_output=True, text=True).stdout.strip()
        print("   Disk usage:", du or "(кеш пуст: модели скачаются при первом использовании)")
    except Exception:
        pass
    return hf_cache_dir


def _colab_token():
    from google.colab import userdata
    return userdata.get("HF_TOKEN")


def init_notebook_config(repo_dir, program_version, mode, output_dir, init_config=None, get_token=None):
    """Проверяет репозиторий, добавляет его в sys.path, читает токен HF (если есть) и строит конфиг."""
    if not os.path.isdir(repo_dir):
        raise RuntimeError("Репозиторий не найден. Сначала запусти ячейку 🚀 Старт сверху "
                           "(после перезапуска среды её нужно запускать заново).")
    if repo_dir not in sys.path:
        sys.path.insert(0, repo_dir)
    try:
        hf_token = (get_token or _colab_token)()
    except Exception:
        hf_token = None  # токена нет: открытые модели работают без него
    if init_config is None:
        from scripts.config import init_config
    return init_config(model_variant=program_version, output_dir=output_dir, hf_token=hf_token, mode=mode)


def preload_modules():
    """Подгружает утилиты и загрузчики; возвращает то, что ячейки используют как переменные ноутбука."""
    from scripts.loaders import reset_pipes
    from scripts.logger import log_error, log_info
    from scripts.utils import free_memory
    return {"free_memory": free_memory, "reset_pipes": reset_pipes, "log_info": log_info, "log_error": log_error}


def style_defaults():
    """Стиль по умолчанию: режимы работают, даже если ячейку «Стиль и проект» не запускали."""
    from scripts.prompt_builder import build_style
    return {"base_style": "illustration", "color_tone": "vintage", "negative": "", "style_extra": "",
            "style_suffix": build_style(style="illustration", tone="vintage"), "active_preset": None}


def setup_all(repo_dir, program_version, mode, output_dir, drive_mount, hf_cache_dir,
              mount=None, install=None, init=None, preload=None):
    """
    Всё, что нужно запустить один раз в начале сеанса, по порядку: Drive и кеш, установка зависимостей,
    конфиг, утилиты и загрузчики. Возвращает словарь переменных ноутбука (CONFIG, DEFAULTS и другие).
    """
    mount_drive_and_cache(drive_mount, hf_cache_dir, **({"mount": mount} if mount else {}))
    (install or install_dependencies)(mode)
    config, variant, defaults, auto_upscale = (init or init_notebook_config)(repo_dir, program_version, mode, output_dir)
    extra = (preload or preload_modules)()
    from scripts.notebook_version import NOTEBOOK_VERSION
    print(f"🎨 Версия ноутбука в репозитории: {NOTEBOOK_VERSION} (должна совпасть с названием ноутбука)")
    print(f"✅ Готово: {program_version} | {mode} | вывод {config['OUTPUT_DIR']}")
    return {"CONFIG": config, "VARIANT": variant, "DEFAULTS": defaults, "AUTO_UPSCALE": auto_upscale,
            **style_defaults(), **extra}
