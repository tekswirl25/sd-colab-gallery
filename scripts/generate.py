# scripts/generate.py
# Автор: genai_colab. Генерация для ячеек основного ноутбука. В ячейке остаются только поля
# и вызов; вся логика здесь. Тяжёлые зависимости (loaders, utils) импортируются при вызове,
# их можно подменить (тесты без GPU).

import time


def run_text2img(config, defaults, user_prompt, seed, n, style_suffix="", negative="",
                 active_preset=None, get_pipe=None, save=None, variant_models=None):
    """
    Text2Img: n картинок с последовательными seed. Шаги, cfg и размер берутся из active_preset
    (ячейка «Проект и стиль»), чего в нём нет, берётся из defaults. Возвращает список путей PNG.
    """
    import torch

    if get_pipe is None:
        from scripts.loaders import get_txt2img_pipe as get_pipe
    if save is None:
        from scripts.utils import save_image_and_meta as save
    if variant_models is None:
        from scripts.config import VARIANT_MODELS as variant_models

    final_prompt = f"{user_prompt}, {style_suffix}" if style_suffix else user_prompt
    variant = config["MODEL_VARIANT"]
    pipe = get_pipe(variant_models[variant]["txt2img"], config["DEVICE"], config["DTYPE"])

    preset = active_preset or {}
    steps = preset.get("steps", defaults["txt2img_steps"])
    cfg_scale = preset.get("cfg", defaults["txt2img_cfg"])
    height = preset.get("height", defaults["img_size"][0])
    width = preset.get("width", defaults["img_size"][1])

    base_seed = int(seed) if seed and int(seed) > 0 else int(torch.seed())

    saved = []
    for i in range(int(n)):
        current_seed = base_seed + i
        out = pipe(
            prompt=final_prompt,
            negative_prompt=(negative or None),
            height=height, width=width,
            guidance_scale=cfg_scale,
            num_inference_steps=steps,
            generator=torch.manual_seed(current_seed),
        )
        meta = {
            "mode": "text2img",
            "prompt": final_prompt,
            "negative": negative,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "size": [height, width],
            "seed": current_seed,
            "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        }
        path, _ = save(out.images[0], prefix="text2img", meta=meta,
                       output_dir=config["OUTPUT_DIR"], mode="text2img")
        saved.append(path)
    print(f"✅ Text2Img: сохранено {len(saved)} в {config['OUTPUT_DIR']}/text2img")
    return saved


# ───────────────────────── Img2Img, ControlNet, Inpaint, Upscale ─────────────────────────

def _final_prompt(user_prompt, base_style, color_tone, style_extra):
    from scripts.prompt_builder import build_prompt
    return build_prompt(text=user_prompt, style=base_style, tone=color_tone, extra=style_extra)


def _need_file(path, kind, label, hint):
    """Путь должен быть задан и существовать; иначе понятная ошибка с подсказкой, что запустить."""
    import os
    if not path:
        raise ValueError(f"⚠️ {label} не задан. {hint}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"⚠️ Файл не найден: {path}")
    return path


def _uploaded(kind):
    from scripts import notebook_uploads
    return notebook_uploads.get_path(kind)


def _tools(get_pipe, save, variant_models):
    if save is None:
        from scripts.utils import save_image_and_meta as save
    if variant_models is None:
        from scripts.config import VARIANT_MODELS as variant_models
    return save, variant_models


def _report(title, img_path, meta_path):
    print(f"✅ {title} completed.")
    print("📂 Saved:", img_path)
    print("🧾 Meta:", meta_path)


def run_img2img(config, defaults, user_prompt, seed, strength, base_style, color_tone, style_extra, negative,
                src_path=None, get_pipe=None, save=None, variant_models=None):
    """Img2Img: фото -> иллюстрация. Исходник: src_path или файл из ячейки Upload. Возвращает (картинка, json)."""
    import torch
    from PIL import Image
    if get_pipe is None:
        from scripts.loaders import get_img2img_pipe as get_pipe
    save, variant_models = _tools(get_pipe, save, variant_models)

    src_path = _need_file(src_path or _uploaded("img2img"), "img2img", "src_path",
                          "Запусти Upload-ячейку выше и нажми 'Use path →'")
    print(f"✅ src_path = {src_path}")
    final_prompt = _final_prompt(user_prompt, base_style, color_tone, style_extra)
    pipe = get_pipe(variant_models[config["MODEL_VARIANT"]]["img2img"], config["DEVICE"], config["DTYPE"])
    out = pipe(
        prompt=final_prompt, negative_prompt=negative or None,
        image=Image.open(src_path).convert("RGB"), strength=strength,
        num_inference_steps=defaults["img2img_steps"], guidance_scale=defaults["img2img_cfg"],
        generator=torch.manual_seed(seed),
    )
    meta = {"mode": "img2img", "prompt": final_prompt, "negative": negative,
            "steps": defaults["img2img_steps"], "cfg_scale": defaults["img2img_cfg"], "strength": strength,
            "seed": seed, "source_path": src_path, "timestamp": time.strftime("%Y%m%d_%H%M%S")}
    paths = save(out.images[0], prefix="img2img", meta=meta, output_dir=config["OUTPUT_DIR"], mode="img2img")
    _report("Img2Img", *paths)
    return paths


def run_controlnet(config, defaults, user_prompt, seed, low_thr, high_thr, base_style, color_tone, style_extra,
                   negative, control_path=None, get_pipe=None, save=None, variant_models=None, canny=None):
    """ControlNet (Canny): контуры фото задают композицию. Возвращает (картинка, json)."""
    import torch
    from PIL import Image
    if get_pipe is None:
        from scripts.loaders import get_controlnet_pipe as get_pipe
    if canny is None:
        from scripts.utils import canny_from_image as canny
    save, variant_models = _tools(get_pipe, save, variant_models)

    control_path = _need_file(control_path or _uploaded("controlnet"), "controlnet", "control_path",
                              "Запусти Upload-ячейку выше и нажми 'Use path →'")
    print(f"✅ control_path = {control_path}")
    final_prompt = _final_prompt(user_prompt, base_style, color_tone, style_extra)
    models = variant_models[config["MODEL_VARIANT"]]
    pipe = get_pipe(models.get("controlnet_model", models["txt2img"]), models["controlnet"],
                    config["DEVICE"], config["DTYPE"])
    src_img = Image.open(control_path).convert("RGB")
    control_img = canny(src_img, low=low_thr, high=high_thr)
    # image= у ControlNet-пайплайна и есть карта контуров (как в режимах USA Safari)
    out = pipe(
        prompt=final_prompt, negative_prompt=negative or None, image=control_img,
        num_inference_steps=defaults["controlnet_steps"], guidance_scale=defaults["controlnet_cfg"],
        generator=torch.manual_seed(seed),
    )
    meta = {"mode": "controlnet", "prompt": final_prompt, "negative": negative,
            "steps": defaults["controlnet_steps"], "cfg_scale": defaults["controlnet_cfg"], "seed": seed,
            "source_path": control_path, "canny": {"low": low_thr, "high": high_thr},
            "timestamp": time.strftime("%Y%m%d_%H%M%S")}
    paths = save(out.images[0], prefix="controlnet", meta=meta, output_dir=config["OUTPUT_DIR"], mode="controlnet")
    _report("ControlNet", *paths)
    print(f"⚙️ Thresholds: low={low_thr}, high={high_thr}")
    return paths


def run_inpaint(config, defaults, user_prompt, seed, strength, base_style, color_tone, style_extra, negative,
                src_path=None, mask_path=None, get_pipe=None, save=None, variant_models=None):
    """Inpainting: белое в маске заменяется, чёрное сохраняется. Возвращает (картинка, json)."""
    import torch
    from PIL import Image
    if get_pipe is None:
        from scripts.loaders import get_inpaint_pipe as get_pipe
    save, variant_models = _tools(get_pipe, save, variant_models)

    src_path = _need_file(src_path or _uploaded("inpaint_image"), "inpaint_image", "image",
                          "Run Upload image cell first.")
    mask_path = _need_file(mask_path or _uploaded("inpaint_mask"), "inpaint_mask", "mask",
                           "Run Upload mask cell first.")
    print(f"✅ image = {src_path}")
    print(f"✅ mask  = {mask_path}")
    final_prompt = _final_prompt(user_prompt, base_style, color_tone, style_extra)
    pipe = get_pipe(variant_models[config["MODEL_VARIANT"]]["inpaint"], config["DEVICE"], config["DTYPE"])
    image = Image.open(src_path).convert("RGB")
    mask = Image.open(mask_path).convert("RGB")
    if mask.size != image.size:
        mask = mask.resize(image.size, Image.LANCZOS)
    out = pipe(
        prompt=final_prompt, negative_prompt=negative or None, image=image, mask_image=mask, strength=strength,
        num_inference_steps=defaults["inpaint_steps"], guidance_scale=defaults["inpaint_cfg"],
        generator=torch.manual_seed(seed),
    )
    meta = {"mode": "inpaint", "prompt": final_prompt, "negative": negative,
            "steps": defaults["inpaint_steps"], "cfg_scale": defaults["inpaint_cfg"], "strength": strength,
            "seed": seed, "source_path": src_path, "mask_path": mask_path,
            "timestamp": time.strftime("%Y%m%d_%H%M%S")}
    paths = save(out.images[0], prefix="inpaint", meta=meta, output_dir=config["OUTPUT_DIR"], mode="inpaint")
    _report("Inpainting", *paths)
    return paths


def run_upscale(config, in_path, seed, prompt="", get_pipe=None, save=None, variant_models=None):
    """Апскейл x4. Возвращает путь к сохранённой картинке."""
    import torch
    from PIL import Image
    if get_pipe is None:
        from scripts.loaders import get_upscale_pipe as get_pipe
    save, variant_models = _tools(get_pipe, save, variant_models)

    if not in_path:
        raise ValueError("Нужно указать путь к изображению для апскейла (in_path)")
    pipe = get_pipe(variant_models[config["MODEL_VARIANT"]]["upscale"], config["DEVICE"], config["DTYPE"])
    out = pipe(image=Image.open(in_path).convert("RGB"), prompt=prompt, generator=torch.manual_seed(seed))
    meta = {"mode": "upscale_x4", "prompt": prompt, "seed": seed, "timestamp": time.strftime("%Y%m%d_%H%M%S")}
    path, _ = save(out.images[0], prefix="upscale", meta=meta, output_dir=config["OUTPUT_DIR"], mode="upscale")
    print(f"✅ Upscale saved: {path}")
    return path
