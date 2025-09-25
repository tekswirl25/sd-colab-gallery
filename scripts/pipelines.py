# scripts/pipelines.py

import torch
from scripts.loaders import (
    get_txt2img_pipe,
    get_img2img_pipe,
    get_controlnet_pipe,
    get_upscale_pipe,
)
from scripts.prompt_builder import build_prompt
from scripts.utils import save_image_and_meta, ts_now
from scripts.logger import log_info
from scripts.config import VARIANT_MODELS


def run_txt2img(user_prompt, style, tone, negative, CONFIG, DEFAULTS, seed=12345, n=1):
    """Генерация изображений из текста"""
    final_prompt = build_prompt(user_prompt, style=style, tone=tone)

    variant = CONFIG["MODEL_VARIANT"]
    model_id = VARIANT_MODELS[variant]["txt2img"]
    pipe = get_txt2img_pipe(model_id, CONFIG["DEVICE"], CONFIG["DTYPE"])

    results = []
    for _ in range(n):
        generator = torch.manual_seed(seed)
        out = pipe(
            prompt=final_prompt,
            negative_prompt=negative or None,
            height=DEFAULTS["img_size"][0],
            width=DEFAULTS["img_size"][1],
            guidance_scale=DEFAULTS["txt2img_cfg"],
            num_inference_steps=DEFAULTS["txt2img_steps"],
            generator=generator,
        )
        im = out.images[0]
        meta = {
            "mode": "text2img",
            "prompt": final_prompt,
            "negative": negative,
            "steps": DEFAULTS["txt2img_steps"],
            "cfg_scale": DEFAULTS["txt2img_cfg"],
            "size": DEFAULTS["img_size"],
            "seed": seed,
            "timestamp": ts_now(),
        }
        p, _ = save_image_and_meta(im, prefix="text2img", meta=meta, output_dir=CONFIG["OUTPUT_DIR"])
        results.append(p)

    log_info(f"Text2Img saved: {results}")
    return results


def run_img2img(user_prompt, style, tone, negative, src_path, CONFIG, DEFAULTS, strength=0.6, seed=12345):
    """Преобразование изображения"""
    from PIL import Image
    final_prompt = build_prompt(user_prompt, style=style, tone=tone)

    variant = CONFIG["MODEL_VARIANT"]
    model_id = VARIANT_MODELS[variant]["img2img"]

    image = Image.open(src_path).convert("RGB")
    pipe_i2i = get_img2img_pipe(model_id, CONFIG["DEVICE"], CONFIG["DTYPE"])

    generator = torch.manual_seed(seed)
    out = pipe_i2i(
        prompt=final_prompt,
        negative_prompt=negative or None,
        image=image,
        strength=strength,
        generator=generator,
    )

    im = out.images[0]
    meta = {
        "mode": "img2img",
        "prompt": final_prompt,
        "negative": negative,
        "strength": strength,
        "seed": seed,
        "timestamp": ts_now(),
    }
    p, _ = save_image_and_meta(im, prefix="img2img", meta=meta, output_dir=CONFIG["OUTPUT_DIR"])
    log_info(f"Img2Img saved: {p}")
    return p


def run_controlnet(user_prompt, style, tone, negative, src_path, CONFIG, DEFAULTS, strength=1.0, seed=12345):
    """ControlNet (например, Canny)"""
    from PIL import Image
    final_prompt = build_prompt(user_prompt, style=style, tone=tone)

    variant = CONFIG["MODEL_VARIANT"]
    model_id = VARIANT_MODELS[variant]["controlnet"]

    image = Image.open(src_path).convert("RGB")
    pipe_cn = get_controlnet_pipe(model_id, CONFIG["DEVICE"], CONFIG["DTYPE"])

    generator = torch.manual_seed(seed)
    out = pipe_cn(
        prompt=final_prompt,
        negative_prompt=negative or None,
        image=image,
        num_inference_steps=DEFAULTS["controlnet_steps"],
        guidance_scale=DEFAULTS["controlnet_cfg"],
        generator=generator,
    )

    im = out.images[0]
    meta = {
        "mode": "controlnet",
        "prompt": final_prompt,
        "negative": negative,
        "steps": DEFAULTS["controlnet_steps"],
        "cfg_scale": DEFAULTS["controlnet_cfg"],
        "seed": seed,
        "timestamp": ts_now(),
    }
    p, _ = save_image_and_meta(im, prefix="controlnet", meta=meta, output_dir=CONFIG["OUTPUT_DIR"])
    log_info(f"ControlNet saved: {p}")
    return p


def run_upscale(src_path, CONFIG):
    """Апскейл изображения"""
    from PIL import Image

    variant = CONFIG["MODEL_VARIANT"]
    model_id = VARIANT_MODELS[variant]["upscale"]

    image = Image.open(src_path).convert("RGB")
    pipe_up = get_upscale_pipe(model_id, CONFIG["DEVICE"], CONFIG["DTYPE"])

    out = pipe_up(prompt="", image=image)
    im = out.images[0]
    meta = {
        "mode": "upscale",
        "timestamp": ts_now(),
    }
    p, _ = save_image_and_meta(im, prefix="upscale", meta=meta, output_dir=CONFIG["OUTPUT_DIR"])
    log_info(f"Upscale saved: {p}")
    return p
