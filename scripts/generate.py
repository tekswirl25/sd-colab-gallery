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
