# scripts/loaders.py

import torch
from diffusers import (
    StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline,
    StableDiffusionUpscalePipeline, ControlNetModel, StableDiffusionXLControlNetPipeline,
    DiffusionPipeline
)
from scripts.logger import log_info, log_error

_txt2img_pipe = None
_img2img_pipe = None
_controlnet_pipe = None
_upscale_pipe = None

def _enable_xformers(pipe):
    try: pipe.enable_xformers_memory_efficient_attention()
    except Exception as e: log_error(f"xFormers not enabled: {e}")
    return pipe

def get_txt2img_pipe(model_id, device, dtype):
    global _txt2img_pipe
    if _txt2img_pipe is None:
        try:
            log_info(f"Loading txt2img: {model_id}")
            _txt2img_pipe = StableDiffusionXLPipeline.from_pretrained(model_id, torch_dtype=dtype)
            _enable_xformers(_txt2img_pipe).to(device)
        except Exception as e: log_error(f"txt2img failed: {e}"); raise
    return _txt2img_pipe

def get_img2img_pipe(model_id, device, dtype):
    global _img2img_pipe
    if _img2img_pipe is None:
        try:
            log_info(f"Loading img2img: {model_id}")
            _img2img_pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, torch_dtype=dtype)
            _enable_xformers(_img2img_pipe).to(device)
        except Exception as e: log_error(f"img2img failed: {e}"); raise
    return _img2img_pipe

def get_controlnet_pipe(model_id, controlnet_id, device, dtype):
    global _controlnet_pipe
    if _controlnet_pipe is None:
        try:
            log_info(f"Loading ControlNet: {model_id}+{controlnet_id}")
            cn = ControlNetModel.from_pretrained(controlnet_id, torch_dtype=dtype)
            _controlnet_pipe = StableDiffusionXLControlNetPipeline.from_pretrained(model_id, controlnet=cn, torch_dtype=dtype)
            _enable_xformers(_controlnet_pipe).to(device)
        except Exception as e: log_error(f"ControlNet failed: {e}"); raise
    return _controlnet_pipe

def get_upscale_pipe(model_id, device, dtype):
    global _upscale_pipe
    if _upscale_pipe is None:
        try:
            log_info(f"Loading Upscaler: {model_id}")
            _upscale_pipe = StableDiffusionUpscalePipeline.from_pretrained(model_id, torch_dtype=dtype)
            _enable_xformers(_upscale_pipe).to(device)
        except Exception as e: log_error(f"Upscaler failed: {e}"); raise
    return _upscale_pipe
