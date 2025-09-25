import os, torch
from scripts.logger import log_info

VARIANTS = {
    "SDXL": {
        "imports": [
            "StableDiffusionXLPipeline",
            "StableDiffusionXLImg2ImgPipeline",
            "StableDiffusionUpscalePipeline",
            "ControlNetModel",
            "StableDiffusionXLControlNetPipeline",
        ],
        "auto_upscale": False,
        "defaults": {
            "txt2img_steps": 30,
            "txt2img_cfg": 6.5,
            "img_size": (1024, 1024),
            "img2img_steps": 30,
            "img2img_cfg": 6.5,
            "controlnet_steps": 30,
            "controlnet_cfg": 6.5,
        }
    },
    "TURBO": {
        "imports": [
            "StableDiffusionXLPipeline",
            "StableDiffusionXLImg2ImgPipeline",
        ],
        "auto_upscale": False,
        "defaults": {
            "txt2img_steps": 4,
            "txt2img_cfg": 1.0,
            "img_size": (512, 512),
            "img2img_steps": 6,
            "img2img_cfg": 1.5,
            "controlnet_steps": 8,
            "controlnet_cfg": 1.5,
        }
    },
    "SD15": {
        "imports": ["DiffusionPipeline"],
        "auto_upscale": True,
        "defaults": {
            "txt2img_steps": 50,
            "txt2img_cfg": 7.5,
            "img_size": (512, 512),
            "img2img_steps": 50,
            "img2img_cfg": 7.5,
            "controlnet_steps": 50,
            "controlnet_cfg": 7.5,
        }
    }
}

# Добавить в scripts/config.py (после VARIANTS)
VARIANT_MODELS = {
    "SDXL": {
        "txt2img":   "stabilityai/stable-diffusion-xl-base-1.0",
        "img2img":   "stabilityai/stable-diffusion-xl-base-1.0",
        "controlnet":"diffusers/controlnet-canny-sdxl-1.0",
        "upscale":   "stabilityai/stable-diffusion-x4-upscaler",
    },
    "TURBO": {
        "txt2img":   "stabilityai/sdxl-turbo",
        "img2img":   "stabilityai/sdxl-turbo",
        # Для ControlNet под Turbo используем SDXL base как базовую модель пайплайна:
        "controlnet_model": "stabilityai/stable-diffusion-xl-base-1.0",
        "controlnet":       "diffusers/controlnet-canny-sdxl-1.0",
        "upscale":   "stabilityai/stable-diffusion-x4-upscaler",
    },
    "SD15": {
        "txt2img":   "runwayml/stable-diffusion-v1-5",
        "img2img":   "runwayml/stable-diffusion-v1-5",
        "controlnet":"lllyasviel/sd-controlnet-canny",
        "upscale":   "stabilityai/stable-diffusion-x4-upscaler",
    },
    # общие дефолты для окружения:
    "device": "cuda",
    "dtype":  "fp16",
}

SUPPORTED_MODES = ("CPU", "GPU_BASIC", "GPU_OPTIMAL")


def init_config(model_variant: str = "SDXL",
                output_dir: str = "/content/outputs",
                hf_token: str | None = None,
                mode: str = "GPU_OPTIMAL",
                env_mode: str = "GPU"):
    """
    Централизованная инициализация конфига.
    - Гарантирует наличие output_dir
    - Настраивает токен HF (если передан или уже есть в окружении)
    - Определяет DEVICE/DTYPE по mode и env_mode
    - Возвращает CONFIG, VARIANT, DEFAULTS, AUTO_UPSCALE
    """

    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported MODE='{mode}'. Use one of {SUPPORTED_MODES}")

    # 1) Токен HF: аргумент > HF_TOKEN > HUGGING_FACE_HUB_TOKEN
    env_hf_token = hf_token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if env_hf_token:
        os.environ["HF_TOKEN"] = env_hf_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = env_hf_token
        log_info("HF token is set via environment")

    # 2) Папка вывода
    os.makedirs(output_dir, exist_ok=True)

    # 3) Параметры варианта
    VARIANT = VARIANTS[model_variant]
    DEFAULTS = VARIANT["defaults"]
    AUTO_UPSCALE = VARIANT["auto_upscale"]

    # 4) Железо/точность по MODE + ENV_MODE
    if env_mode == "CPU":
        device = "cpu"
        dtype = torch.float32
    else:  # GPU по умолчанию
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            # запрошен GPU-режим, но GPU недоступен — откат на CPU
            log_info("GPU not available -> falling back to CPU mode")
            dtype = torch.float32
        else:
            # оба GPU-режима используют fp16; отличие в политике оптимизаций на уровне пайплайнов
            dtype = torch.float16

    CONFIG = {
        "MODE": mode,
        "MODEL_VARIANT": model_variant,
        "OUTPUT_DIR": output_dir,
        "DEVICE": device,
        "DTYPE": dtype,
    }

    log_info(
        f"Config initialized: "
        f"MODEL_VARIANT={model_variant}, MODE={mode}, ENV_MODE={env_mode}, OUTPUT_DIR={output_dir}, "
        f"DEVICE={device}, DTYPE={dtype}"
    )
    return CONFIG, VARIANT, DEFAULTS, AUTO_UPSCALE
