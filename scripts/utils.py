# scripts/utils.py

import os, gc, datetime, json
from PIL import Image
import numpy as np, cv2, torch
from scripts.logger import log_info, log_error
from datetime import datetime

def ts_now():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def base_name(prefix): return f"{prefix}_{ts_now()}"

def save_image_and_meta(im, prefix, meta, output_dir, mode="text2img"):
    """
    Save image + metadata JSON + thumbnail.
    Args:
        im (PIL.Image): изображение
        prefix (str): префикс имени файла (например text2img / img2img / controlnet)
        meta (dict): словарь с метаданными
        output_dir (str): корневой каталог (обычно CONFIG["OUTPUT_DIR"])
        mode (str): подрежим ("text2img" / "img2img" / "controlnet")
    Returns:
        tuple: (image_path, meta_path)
    """
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"{prefix}_{ts}.png"

    # Основные папки
    out_dir = Path(output_dir) / mode
    thumb_dir = Path(output_dir) / "thumbnails" / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    # Сохранение картинки
    img_path = out_dir / fname
    im.save(img_path, format="PNG")

    # JSON
    meta_path = out_dir / f"{fname}.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Thumbnail
    thumb_path = thumb_dir / fname.replace(".png", ".jpg")
    thumb = im.copy()
    thumb.thumbnail((128, 128))
    thumb.convert("RGB").save(thumb_path, format="JPEG", quality=85)

    return str(img_path), str(meta_path)

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
