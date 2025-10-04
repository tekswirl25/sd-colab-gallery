# scripts/utils.py

import os, gc, datetime, json
from PIL import Image
import numpy as np, cv2, torch
from scripts.logger import log_info, log_error
from datetime import datetime

def ts_now():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def base_name(prefix): return f"{prefix}_{ts_now()}"

# def save_image_and_meta(img: Image.Image, prefix: str, meta: dict, output_dir: str):
#     try:
#         os.makedirs(output_dir, exist_ok=True)  # ← добавить
#         stem = base_name(prefix)
#         img_path = os.path.join(output_dir, f"{stem}.png")
#         meta_path = os.path.join(output_dir, f"{stem}.json")
#         img.save(img_path)
#         with open(meta_path, 'w') as f:
#             json.dump(meta, f, ensure_ascii=False, indent=2)
#         log_info(f"Saved image: {img_path}")
#         return img_path, meta_path
#     except Exception as e:
#         log_error(f"Error saving image/meta: {e}")
#         raise

def save_image_and_meta(
    im,
    prefix,
    meta,
    output_dir="/content/outputs",
    thumb_dir="/content/thumbnails",
    thumb_size=(128, 128),
    mode="text2img"
):
    """
    Сохраняет изображение, thumbnail и JSON с метаданными.
    Картинки и JSON раскладываются по подпапкам:
    - /outputs/<mode>/
    - /thumbnails/<mode>/
    """

    # пути по модулю
    out_path = os.path.join(output_dir, mode)
    th_path = os.path.join(thumb_dir, mode)

    os.makedirs(out_path, exist_ok=True)
    os.makedirs(th_path, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{prefix}_{ts}"

    img_path  = os.path.join(out_path, base_name + ".png")
    meta_path = os.path.join(out_path, base_name + ".json")
    thumb_path = os.path.join(th_path, base_name + "_thumb.jpg")

    # сохраняем оригинал
    im.save(img_path)

    # thumbnail
    im_thumb = im.copy()
    im_thumb.thumbnail(thumb_size)
    im_thumb.save(thumb_path, "JPEG", quality=85)

    # дописываем thumbnail в метаданные
    meta["thumbnail"] = os.path.relpath(thumb_path, out_path)

    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return img_path, meta_path

def free_memory():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    log_info("Memory cleared.")

def list_images(folder):
    return sorted(
        [f for f in os.listdir(folder) if f.lower().endswith((".png",".jpg",".jpeg",".webp"))],
        key=lambda x: os.path.getmtime(os.path.join(folder, x)),
        reverse=True
    )

def find_latest_image(folder):
    imgs = [os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith((".png",".jpg",".jpeg",".webp"))]
    return max(imgs, key=os.path.getmtime) if imgs else None

def canny_from_image(pil_img: Image.Image, low=100, high=200):
    arr = np.array(pil_img.convert('RGB'))
    edges = cv2.Canny(arr, low, high)
    edges_3c = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(edges_3c)
