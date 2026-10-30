# scripts/usa_safari.py
# USA Safari — Нескучная аналитика
# Загрузка режимов, сборка промптов, роутинг генерации, парсер брифа.

import json
import os
import re
import torch
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from PIL import Image

from scripts.logger import log_info, log_error

PRESETS_DIR = Path("presets")
MODES_FILE  = "usa_safari_modes.json"

# ── Загрузка режимов ──────────────────────────────────────────────────────────

def _load_modes() -> list:
    path = PRESETS_DIR / MODES_FILE
    if not path.exists():
        raise FileNotFoundError(f"Файл режимов не найден: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_mode(mode_id: str) -> dict | None:
    """Возвращает словарь режима по id или None."""
    for m in _load_modes():
        if m["id"] == mode_id:
            return m
    return None


def list_modes() -> list[dict]:
    """Список всех режимов."""
    return _load_modes()


# ── Сборка промптов ───────────────────────────────────────────────────────────

def build_prompts(mode: dict, scene: str, with_character: bool) -> tuple[str, str]:
    """
    Собирает (positive, negative) из режима + содержания сцены.

    positive = prefix стиля + содержание сцены [+ anatomy если with_character]
    negative = base negative [+ anatomy negative если with_character]
    """
    pos_parts = [mode["positive"]]
    if scene:
        pos_parts.append(scene)
    if with_character and mode.get("anatomy_addon"):
        pos_parts.append(mode["anatomy_addon"])
    positive = ", ".join(pos_parts)

    neg_parts = [mode["negative"]]
    if with_character and mode.get("anatomy_negative"):
        neg_parts.append(mode["anatomy_negative"])
    negative = ", ".join(neg_parts)

    return positive, negative


# ── Основная функция генерации ────────────────────────────────────────────────

def run_generation(
    mode: dict,
    positive: str,
    negative: str,
    config: dict,
    output_dir: str,
    src_path:    str | None = None,
    mask_path:   str | None = None,
    ip_ref_path: str | None = None,
) -> str:
    """
    Роутит генерацию в нужный пайплайн (text2img / img2img / inpaint).

    Параметры:
        mode        – словарь режима из usa_safari_modes.json
        positive    – собранный positive prompt (из build_prompts)
        negative    – собранный negative prompt
        config      – CONFIG из Colab (MODEL_VARIANT, DEVICE, DTYPE, OUTPUT_DIR)
        output_dir  – папка для сохранения
        src_path    – путь к base image (нужен для img2img / inpaint)
        mask_path   – путь к маске (нужен для inpaint)
        ip_ref_path – путь к reference image для IP-Adapter (опционально)

    Возвращает путь к сохранённому PNG.
    """
    from scripts.loaders import get_txt2img_pipe, get_img2img_pipe, get_inpaint_pipe
    from scripts.config import VARIANT_MODELS
    from scripts.utils import save_image_and_meta

    mode_type = mode["mode_type"]
    variant   = config["MODEL_VARIANT"]
    device    = config["DEVICE"]
    dtype     = config["DTYPE"]

    steps = mode.get("steps", 30)
    cfg   = mode.get("cfg",   7.0)
    w     = mode.get("width",  1280)
    h     = mode.get("height",  720)
    seed  = mode.get("seed",   -1)

    # ── Seed ─────────────────────────────────────────
    if seed and seed > 0:
        actual_seed = int(seed)
    else:
        actual_seed = int(torch.seed() & 0x7FFFFFFF)
        print(f"🌱 Random seed: {actual_seed}")
    generator = torch.Generator(device=device).manual_seed(actual_seed)

    stack = ExitStack()  # выгружает IP-Adapter после кадра, даже при ошибке
    # ── Генерация ─────────────────────────────────────
    with stack:
        if mode_type == "text2img":
            model_id = VARIANT_MODELS[variant]["txt2img"]
            pipe = get_txt2img_pipe(model_id, device, dtype)

            if ip_ref_path and _use_ip_adapter(stack, pipe, variant):
                ref_img = Image.open(ip_ref_path).convert("RGB")
                out = pipe(
                    prompt=positive, negative_prompt=negative,
                    num_inference_steps=steps, guidance_scale=cfg,
                    width=w, height=h, generator=generator,
                    ip_adapter_image=ref_img,
                )
            else:
                out = pipe(
                    prompt=positive, negative_prompt=negative,
                    num_inference_steps=steps, guidance_scale=cfg,
                    width=w, height=h, generator=generator,
                )
            image = out.images[0]

        elif mode_type == "controlnet":
            if not src_path:
                raise ValueError("⚠️ Для ControlNet нужен source image — загрузи файл в поле «Base image» выше.")
            from scripts.loaders import get_controlnet_pipe

            cn_type   = mode.get("controlnet_type", "canny")
            cn_key    = f"controlnet_{cn_type}"
            cn_id     = VARIANT_MODELS[variant].get(cn_key) or VARIANT_MODELS[variant]["controlnet"]
            # для SDXL_TURBO база ControlNet — обычный SDXL (как в ячейке ControlNet ноутбука)
            base_id   = VARIANT_MODELS[variant].get("controlnet_model", VARIANT_MODELS[variant]["txt2img"])

            src_img     = Image.open(src_path).convert("RGB").resize((w, h))
            control_img = _preprocess_controlnet(src_img, cn_type)

            print(f"🔧 ControlNet: {cn_type} | model: {cn_id.split('/')[-1]}")
            pipe = get_controlnet_pipe(base_id, cn_id, device, dtype)

            pipe_kwargs = dict(
                prompt=positive, negative_prompt=negative,
                image=control_img,
                num_inference_steps=steps, guidance_scale=cfg,
                generator=generator,
            )
            if ip_ref_path and _use_ip_adapter(stack, pipe, variant):
                pipe_kwargs["ip_adapter_image"] = Image.open(ip_ref_path).convert("RGB")

            out   = pipe(**pipe_kwargs)
            image = out.images[0]

        elif mode_type == "img2img":
            # Fallback — используется если controlnet_aux недоступен
            if not src_path:
                raise ValueError("⚠️ Для img2img нужен base image — загрузи файл в поле «Base image» выше.")
            model_id = VARIANT_MODELS[variant]["img2img"]
            pipe     = get_img2img_pipe(model_id, device, dtype)
            src_img  = Image.open(src_path).convert("RGB").resize((w, h))
            denoising = mode.get("denoising", 0.65)

            if ip_ref_path and _use_ip_adapter(stack, pipe, variant):
                ref_img = Image.open(ip_ref_path).convert("RGB")
                out = pipe(
                    prompt=positive, negative_prompt=negative,
                    image=src_img, strength=denoising,
                    num_inference_steps=steps, guidance_scale=cfg,
                    generator=generator, ip_adapter_image=ref_img,
                )
            else:
                out = pipe(
                    prompt=positive, negative_prompt=negative,
                    image=src_img, strength=denoising,
                    num_inference_steps=steps, guidance_scale=cfg,
                    generator=generator,
                )
            image = out.images[0]

        elif mode_type == "inpaint":
            if not src_path:
                raise ValueError("⚠️ Для inpaint нужен source image — загрузи в поле «Base image» выше.")
            if not mask_path:
                raise ValueError("⚠️ Для inpaint нужна маска — загрузи в поле «Mask» выше.")

            model_id = VARIANT_MODELS[variant]["inpaint"]
            pipe     = get_inpaint_pipe(model_id, device, dtype)
            src_img  = Image.open(src_path).convert("RGB")
            mask_img = Image.open(mask_path).convert("RGB")

            # Размер должен делиться на 8
            orig_w, orig_h = src_img.size
            safe_w = (orig_w // 8) * 8
            safe_h = (orig_h // 8) * 8
            if (safe_w, safe_h) != (orig_w, orig_h):
                src_img  = src_img.resize((safe_w, safe_h))
                mask_img = mask_img.resize((safe_w, safe_h))

            denoising = mode.get("denoising", 0.80)
            out = pipe(
                prompt=positive, negative_prompt=negative,
                image=src_img, mask_image=mask_img, strength=denoising,
                num_inference_steps=steps, guidance_scale=cfg,
                generator=generator,
            )
            image = out.images[0]

        else:
            raise ValueError(f"Неизвестный mode_type: {mode_type!r}")

    # ── Сохранение ────────────────────────────────────
    meta = {
        "usa_safari_mode":  mode["id"],
        "mode_type":        mode_type,
        "prompt":           positive,
        "negative_prompt":  negative,
        "seed":             actual_seed,
        "steps":            steps,
        "cfg":              cfg,
        "denoising":        mode.get("denoising"),
    }
    img_path, _ = save_image_and_meta(image, mode["id"], meta, output_dir, mode=mode_type)
    log_info(f"USA Safari saved: {img_path}")

    # ── Логируем seed в Drive (если смонтирован) ──────
    _log_seed(actual_seed, mode["id"], positive, img_path)

    return img_path


# ── ControlNet preprocessors ─────────────────────────────────────────────────

def _preprocess_controlnet(pil_img: Image.Image, cn_type: str) -> Image.Image:
    """
    Препроцессинг исходного изображения для ControlNet.

    canny    → edges (OpenCV, встроен в utils)
    openpose → skeleton (controlnet_aux, устанавливается отдельно)
    depth    → depth map (controlnet_aux)
    """
    if cn_type == "canny":
        from scripts.utils import canny_from_image
        return canny_from_image(pil_img, low=100, high=200)

    elif cn_type == "openpose":
        try:
            from controlnet_aux import OpenposeDetector
            detector = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
            return detector(pil_img)
        except ImportError:
            log_error("controlnet_aux не установлен — fallback на Canny. "
                      "Установи: pip install controlnet_aux")
            print("⚠️ controlnet_aux не установлен, использую Canny как замену OpenPose.")
            from scripts.utils import canny_from_image
            return canny_from_image(pil_img, low=100, high=200)

    elif cn_type == "depth":
        try:
            from controlnet_aux import MidasDetector
            detector = MidasDetector.from_pretrained("lllyasviel/Annotators")
            return detector(pil_img)
        except ImportError:
            log_error("controlnet_aux не установлен — fallback на Canny.")
            from scripts.utils import canny_from_image
            return canny_from_image(pil_img, low=50, high=150)

    else:
        raise ValueError(f"Неизвестный controlnet_type: {cn_type!r}")


# ── IP-Adapter ────────────────────────────────────────────────────────────────

def _use_ip_adapter(stack: ExitStack, pipe, variant: str) -> bool:
    """
    Подключает IP-Adapter и регистрирует его выгрузку в stack.

    Пайплайны кэшируются (loaders.py). Если оставить адаптер загруженным,
    следующий кадр без референса падает: пайплайн ждёт ip_adapter_image.
    """
    if _apply_ip_adapter(pipe, variant):
        stack.callback(_unload_ip_adapter, pipe)
        return True
    return False


def _unload_ip_adapter(pipe):
    try:
        pipe.unload_ip_adapter()
    except Exception as e:
        log_error(f"IP-Adapter unload failed: {e}")


def _apply_ip_adapter(pipe, variant: str) -> bool:
    """
    Подключает IP-Adapter к пайплайну для консистентности лица/внешности.

    SD15  → ip-adapter_sd15.bin (h94/IP-Adapter)
    SDXL  → ip-adapter_sdxl.bin (h94/IP-Adapter)

    Для FaceID (лучшего удержания лица при смене поз) — обновить weight_name
    на ip-adapter-faceid_sd15.bin + установить ip_adapter_faceid в pip.
    """
    try:
        if variant in ("SDXL", "SDXL_TURBO"):
            pipe.load_ip_adapter(
                "h94/IP-Adapter",
                subfolder="sdxl_models",
                weight_name="ip-adapter_sdxl.bin",
            )
        else:
            pipe.load_ip_adapter(
                "h94/IP-Adapter",
                subfolder="models",
                weight_name="ip-adapter_sd15.bin",
            )
        pipe.set_ip_adapter_scale(0.6)
        log_info(f"IP-Adapter loaded (variant={variant})")
        return True
    except Exception as e:
        log_error(f"IP-Adapter load failed: {e}")
        print(f"⚠️ IP-Adapter не загружен: {e}\n   Продолжаю генерацию без него.")
        return False


# ── Seeds log ─────────────────────────────────────────────────────────────────

SEEDS_LOG = Path(os.environ.get(
    "USA_SAFARI_SEEDS_LOG",
    "/content/drive/MyDrive/USA Safari Reference/seeds/seeds_log.txt",
))

def _log_seed(seed: int, mode_id: str, positive: str, img_path: str):
    """Дописывает запись в seeds_log.txt на Google Drive."""
    try:
        SEEDS_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fname = Path(img_path).name
        entry = (
            f"[{ts}] seed={seed} | mode={mode_id} | file={fname}\n"
            f"  prompt: {positive[:120]}...\n\n"
        )
        with open(SEEDS_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
        log_info(f"Seed {seed} logged to {SEEDS_LOG}")
    except Exception:
        pass  # Drive не смонтирован или папка недоступна — не критично


# ── Парсер текстового брифа сцены ────────────────────────────────────────────

_MODE_ALIASES = {
    "editorial vo":     "editorial-vo",
    "editorial":        "editorial-vo",
    "vo":               "editorial-vo",
    "stock ref":        "stock-ref-comic",
    "stock":            "stock-ref-comic",
    "news screenshot":  "news-screenshot",
    "screenshot":       "news-screenshot",
    "news":             "news-screenshot",
    "roto":             "roto-video-frame",
    "video frame":      "roto-video-frame",
    "video":            "roto-video-frame",
    "inpaint anatomy":  "inpaint-anatomy",
    "anatomy":          "inpaint-anatomy",
    "inpaint signature":"inpaint-signature",
    "signature":        "inpaint-signature",
    "inpaint face":     "inpaint-face",
    "face":             "inpaint-face",
}

_SOURCE_TYPE_MAP = {
    "stock":        "stock-ref-comic",
    "screenshot":   "news-screenshot",
    "video frame":  "roto-video-frame",
    "video":        "roto-video-frame",
    "roto":         "roto-video-frame",
}


def parse_scene_brief(text: str) -> dict:
    """
    Парсит текстовый бриф сцены в словарь.

    Ожидаемый формат (от сценарного модуля):
        [режим]
        Сцена: содержание
        Персонаж: да / нет
        Если да: силуэт / архетип (краткое описание)
        Исходник: нет / есть (тип: stock / screenshot / video frame)
        IP-Adapter: нет / да (ref: название файла в Drive)

    Возвращает словарь с ключами:
        mode_id, scene, with_character, character_desc,
        has_source, source_type, use_ip_adapter, ip_ref_name
    """
    result = {
        "mode_id":        None,
        "scene":          "",
        "with_character": False,
        "character_desc": "",
        "has_source":     False,
        "source_type":    None,
        "use_ip_adapter": False,
        "ip_ref_name":    None,
    }

    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    for line in lines:
        lo = line.lower()

        # Режим — строка в скобках [режим] или первая нераспознанная строка
        if result["mode_id"] is None:
            m = re.match(r'\[(.+?)\]', line)
            raw = (m.group(1) if m else line).strip().lower()
            if not lo.startswith(("сцена:", "персонаж:", "если", "исходник:", "ip-adapter:")):
                for alias, mode_id in _MODE_ALIASES.items():
                    if alias in raw:
                        result["mode_id"] = mode_id
                        break

        if lo.startswith("сцена:"):
            result["scene"] = line[len("сцена:"):].strip()

        elif lo.startswith("персонаж:"):
            val = line[len("персонаж:"):].strip().lower()
            result["with_character"] = val.startswith("да")

        elif lo.startswith("если да:"):
            result["character_desc"] = line[len("если да:"):].strip()

        elif lo.startswith("исходник:"):
            val = lo[len("исходник:"):].strip()
            result["has_source"] = not val.startswith("нет")
            for src_key, mode_id in _SOURCE_TYPE_MAP.items():
                if src_key in val:
                    result["source_type"] = src_key
                    break

        elif lo.startswith("ip-adapter:"):
            val = line[len("ip-adapter:"):].strip()  # регистр имени файла важен: Drive его различает
            result["use_ip_adapter"] = not val.lower().startswith("нет")
            ref_m = re.search(r'ref:\s*([^\s)]+)', val, re.I)
            if ref_m:
                result["ip_ref_name"] = ref_m.group(1).strip()

    # Если режим не распознан — вывести из has_source + source_type
    if result["mode_id"] is None:
        if not result["has_source"]:
            result["mode_id"] = "editorial-vo"
        else:
            result["mode_id"] = _SOURCE_TYPE_MAP.get(
                result["source_type"] or "", "editorial-vo"
            )

    return result
