import torch
from diffusers import (
    StableDiffusionXLPipeline,
    StableDiffusionXLImg2ImgPipeline,
    StableDiffusionXLControlNetPipeline,
    StableDiffusionUpscalePipeline,
    ControlNetModel,
)
from scripts.logger import log_info, log_error

# === Глобальные кэши пайплайнов и их параметров ===
_txt2img_pipe = None
_txt2img_id = None
_txt2img_dev = None
_txt2img_dtype = None

_img2img_pipe = None
_img2img_id = None
_img2img_dev = None
_img2img_dtype = None

_controlnet_pipe = None
_controlnet_ids = (None, None)  # (base_model_id, controlnet_id)
_controlnet_dev = None
_controlnet_dtype = None

_upscale_pipe = None
_upscale_id = None
_upscale_dev = None
_upscale_dtype = None


# === Вспомогательные функции ===
def _enable_xformers(pipe):
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass
    return pipe


def _same(a, b):
    return str(a) == str(b)


def reset_pipes():
    """Сбросить все кэши пайплайнов (форсировать полную переинициализацию)."""
    global _txt2img_pipe, _img2img_pipe, _controlnet_pipe, _upscale_pipe
    global _txt2img_id, _img2img_id, _controlnet_ids, _upscale_id
    global _txt2img_dev, _img2img_dev, _controlnet_dev, _upscale_dev
    global _txt2img_dtype, _img2img_dtype, _controlnet_dtype, _upscale_dtype

    _txt2img_pipe = _img2img_pipe = _controlnet_pipe = _upscale_pipe = None
    _txt2img_id = _img2img_id = _upscale_id = None
    _controlnet_ids = (None, None)
    _txt2img_dev = _img2img_dev = _controlnet_dev = _upscale_dev = None
    _txt2img_dtype = _img2img_dtype = _controlnet_dtype = _upscale_dtype = None

    log_info("All pipelines have been reset")


# === Фабрики пайплайнов ===
def get_txt2img_pipe(model_id, device, dtype):
    global _txt2img_pipe, _txt2img_id, _txt2img_dev, _txt2img_dtype
    if (
        _txt2img_pipe is None
        or not _same(_txt2img_id, model_id)
        or not _same(_txt2img_dev, device)
        or not _same(_txt2img_dtype, dtype)
    ):
        log_info(f"Loading SDXL txt2img pipeline: id={model_id}, device={device}, dtype={dtype}")
        try:
            pipe = StableDiffusionXLPipeline.from_pretrained(model_id, torch_dtype=dtype)
            _enable_xformers(pipe).to(device)
            _txt2img_pipe, _txt2img_id, _txt2img_dev, _txt2img_dtype = pipe, model_id, device, dtype
        except Exception as e:
            log_error(f"Failed to load txt2img pipeline: {e}")
            raise
    return _txt2img_pipe


def get_img2img_pipe(model_id, device, dtype):
    global _img2img_pipe, _img2img_id, _img2img_dev, _img2img_dtype
    if (
        _img2img_pipe is None
        or not _same(_img2img_id, model_id)
        or not _same(_img2img_dev, device)
        or not _same(_img2img_dtype, dtype)
    ):
        log_info(f"Loading SDXL img2img pipeline: id={model_id}, device={device}, dtype={dtype}")
        try:
            pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, torch_dtype=dtype)
            _enable_xformers(pipe).to(device)
            _img2img_pipe, _img2img_id, _img2img_dev, _img2img_dtype = pipe, model_id, device, dtype
        except Exception as e:
            log_error(f"Failed to load img2img pipeline: {e}")
            raise
    return _img2img_pipe


def get_controlnet_pipe(model_id, controlnet_id, device, dtype):
    global _controlnet_pipe, _controlnet_ids, _controlnet_dev, _controlnet_dtype
    if (
        _controlnet_pipe is None
        or not _same(_controlnet_ids, (model_id, controlnet_id))
        or not _same(_controlnet_dev, device)
        or not _same(_controlnet_dtype, dtype)
    ):
        log_info(
            f"Loading SDXL ControlNet pipeline: base={model_id}, controlnet={controlnet_id}, device={device}, dtype={dtype}"
        )
        try:
            cn = ControlNetModel.from_pretrained(controlnet_id, torch_dtype=dtype)
            pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
                model_id, controlnet=cn, torch_dtype=dtype
            )
            _enable_xformers(pipe).to(device)
            _controlnet_pipe, _controlnet_ids, _controlnet_dev, _controlnet_dtype = (
                pipe,
                (model_id, controlnet_id),
                device,
                dtype,
            )
        except Exception as e:
            log_error(f"Failed to load controlnet pipeline: {e}")
            raise
    return _controlnet_pipe


def get_upscale_pipe(model_id, device, dtype):
    global _upscale_pipe, _upscale_id, _upscale_dev, _upscale_dtype
    if (
        _upscale_pipe is None
        or not _same(_upscale_id, model_id)
        or not _same(_upscale_dev, device)
        or not _same(_upscale_dtype, dtype)
    ):
        log_info(f"Loading Upscale pipeline: id={model_id}, device={device}, dtype={dtype}")
        try:
            pipe = StableDiffusionUpscalePipeline.from_pretrained(model_id, torch_dtype=dtype)
            _enable_xformers(pipe).to(device)
            _upscale_pipe, _upscale_id, _upscale_dev, _upscale_dtype = pipe, model_id, device, dtype
        except Exception as e:
            log_error(f"Failed to load upscale pipeline: {e}")
            raise
    return _upscale_pipe
