# scripts/smoke_check.py
# Автор: genai_colab. Короткая проверка режимов USA Safari на GPU в Colab:
# малый размер и мало шагов, время и пик видеопамяти, отчёт на Drive.
# Все значения (режимы, шаги, размер, папка отчёта) приходят снаружи.

import json
import os
import time
import traceback
from datetime import datetime

from PIL import Image, ImageDraw

# Версия проверки: дата и время (PST) последнего изменения проверки или её ноутбука.
# Меняется при каждой правке: TZ=PST8PDT date +%Y%m%d%H%M%S. Название ноутбука должно её содержать (тест).
SMOKE_VERSION = "20261030163753"

_NEEDS_SOURCE = {"controlnet", "img2img", "inpaint"}


def _default_peak_vram_gb():
    try:
        import torch
        if torch.cuda.is_available():
            return round(torch.cuda.max_memory_allocated() / 1024 ** 3, 2)
    except Exception:
        pass
    return None


def _default_reset_peak():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def _short_traceback(text, max_lines):
    """Заголовок и последние строки стека: по ним видно, где упало."""
    lines = text.rstrip().splitlines()
    if len(lines) > max_lines:
        lines = [lines[0]] + lines[-(max_lines - 1):]
    return "\n".join(lines)


def _make_synthetic_source(path, size):
    """Простая картинка (светлый фон, фигура), чтобы режимам с исходником было что обрабатывать."""
    img = Image.new("RGB", (size, size), (225, 225, 215))
    d = ImageDraw.Draw(img)
    c, r = size // 2, size // 10
    d.ellipse((c - r, size // 5 - r, c + r, size // 5 + r), fill=(60, 60, 60))      # голова
    d.rectangle((c - r, size // 5 + r, c + r, size // 5 + r + size // 3), fill=(90, 90, 120))  # тело
    img.save(path)
    return path


def _make_center_mask(path, size):
    """Чёрная маска с белым квадратом в центре (белое = заменить)."""
    mask = Image.new("L", (size, size), 0)
    q = size // 4
    mask.paste(255, (q, q, size - q, size - q))
    mask.save(path)
    return path


def run_smoke(mode_ids, config, steps, size, report_dir, runner=None, get_mode=None,
              build_prompts=None, scene="a man reading a newspaper at a desk",
              clock=time.perf_counter, peak_vram_gb=_default_peak_vram_gb,
              reset_peak=_default_reset_peak, tb_lines=25, source_path=None):
    """
    Прогоняет режимы по очереди. Сбой одного режима не останавливает остальные.
    Режимам, которым нужен исходник (controlnet, img2img, inpaint), даётся: source_path,
    если задан; иначе картинка первого успешного режима; иначе созданная здесь простая
    картинка. Для inpaint создаётся маска.
    Возвращает отчёт и сохраняет его JSON в report_dir.
    """
    if runner is None or get_mode is None or build_prompts is None:
        from scripts import usa_safari
        runner = runner or usa_safari.run_generation
        get_mode = get_mode or usa_safari.get_mode
        build_prompts = build_prompts or usa_safari.build_prompts

    out_dir = config["OUTPUT_DIR"]
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)

    results, first_output, synthetic = [], None, None
    for mid in mode_ids:
        row = {"mode": mid, "ok": False, "seconds": None, "peak_vram_gb": None, "error": None, "traceback": None, "output": None}
        results.append(row)
        base = get_mode(mid)
        if base is None:
            row["error"] = f"режим {mid!r} не найден"
            continue
        mode = dict(base, steps=steps, width=size, height=size)  # исходный режим не меняем
        kwargs = {}
        if mode["mode_type"] in _NEEDS_SOURCE:
            source = source_path or first_output
            if not source:
                if synthetic is None:
                    synthetic = _make_synthetic_source(os.path.join(out_dir, "smoke_source.png"), size)
                source = synthetic
            kwargs["src_path"] = source
            if mode["mode_type"] == "inpaint":
                kwargs["mask_path"] = _make_center_mask(os.path.join(out_dir, "smoke_mask.png"), size)
        positive, negative = build_prompts(mode, scene, False)
        reset_peak()
        t0 = clock()
        try:
            row["output"] = runner(mode, positive, negative, config, out_dir, **kwargs)
            row["ok"] = True
        except Exception as e:  # отчёт важнее остановки
            row["error"] = f"{type(e).__name__}: {e}"
            row["traceback"] = _short_traceback(traceback.format_exc(), tb_lines)
        row["seconds"] = round(clock() - t0, 2)
        row["peak_vram_gb"] = peak_vram_gb()
        if row["ok"] and first_output is None:
            first_output = row["output"]

    report = {
        "version": SMOKE_VERSION,
        "variant": config["MODEL_VARIANT"],
        "steps": steps,
        "size": size,
        "created": datetime.now().strftime("%Y%m%d%H%M%S"),
        "results": results,
    }
    path = os.path.join(report_dir, f"smoke_v{SMOKE_VERSION}_{report['created']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def format_report(report):
    lines = [f"Версия проверки {report['version']}", f"Проверка: {report['variant']}, {report['size']}px, {report['steps']} шагов"]
    for r in report["results"]:
        status = "OK  " if r["ok"] else "FAIL"
        extra = f"{r['seconds']} c, пик {r['peak_vram_gb']} ГБ" if r["seconds"] is not None else ""
        err = f"  {r['error']}" if r["error"] else ""
        lines.append(f"{status} {r['mode']:<18} {extra}{err}")
        if r.get("traceback"):
            lines.append(r["traceback"])
    return "\n".join(lines)
