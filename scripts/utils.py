# scripts/utils.py

import os, gc, datetime, json
from PIL import Image
import numpy as np, cv2, torch
from scripts.logger import log_info, log_error

def ts_now():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def base_name(prefix): return f"{prefix}_{ts_now()}"

def save_image_and_meta(img: Image.Image, prefix: str, meta: dict, output_dir: str):
    try:
        stem = base_name(prefix)
        img_path = os.path.join(output_dir, f"{stem}.png")
        meta_path = os.path.join(output_dir, f"{stem}.json")
        img.save(img_path)
        with open(meta_path, 'w') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        log_info(f"Saved image: {img_path}")
        return img_path, meta_path
    except Exception as e:
        log_error(f"Error saving image/meta: {e}")
        raise

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
